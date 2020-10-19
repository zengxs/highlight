import re
import weakref
from abc import ABCMeta
from typing import Dict, List, Optional, Union


def obj_proxy(obj):
    if isinstance(obj, weakref.ProxyType):
        return obj
    else:
        return weakref.proxy(obj)


class MatchRegex(object):
    """
    Expandable regex
      used by
      - first_line_match
      - MatchPattern
    """

    syndef: "SyntaxDefinition"

    _regex: str

    def __init__(self, syndef, regex: str):
        self.syndef = obj_proxy(syndef)
        self._regex = regex

    @classmethod
    def create(cls, syndef, regex):
        if regex is None:
            return None
        return cls(syndef, regex)

    def __str__(self) -> str:
        """ Computed regex string """
        return self._expand(self._regex)

    EXPAND_RE = re.compile(r"{{([A-Za-z0-9_]+)}}")

    def _expand(self, regex: str) -> str:
        """ variables expanded (recursive) """
        match = re.search(self.EXPAND_RE, regex)

        while match is not None:  # for multiple variables expansion
            if match is None:
                return regex

            var_name = match.group(1)
            var_value = self.syndef.variables[var_name]
            var_value = self._expand(var_value)  # variable expand

            regex = regex.replace("{{%s}}" % var_name, var_value)

            match = re.search(self.EXPAND_RE, regex)

        return regex


class MatchAction(metaclass=ABCMeta):
    pass


class IntoContextAction(MatchAction):
    pat_ref: "SyntaxPattern"

    # nested context
    _synctx: "SyntaxContext"

    # name ref context
    _ctxname: str

    def __init__(self, pattern, synctx):
        self.pat_ref = obj_proxy(pattern)
        if isinstance(synctx, str):
            self._ctxname = synctx
        elif isinstance(synctx, SyntaxContext):
            self._synctx = synctx
        else:
            raise ValueError

    @property
    def context(self) -> "SyntaxContext":
        """ get ref synctx """
        synctx = getattr(self, "_synctx", None)
        if isinstance(synctx, SyntaxContext):
            return synctx

        ctx_name = getattr(self, "_ctxname", None)
        if isinstance(ctx_name, str):
            return obj_proxy(self.pat_ref.synctx.syndef[ctx_name])


class PushAction(IntoContextAction):
    pass


class SetAction(IntoContextAction):
    pass


class PopAction(MatchAction):
    pass


class SyntaxPattern(metaclass=ABCMeta):
    synctx: "SyntaxContext"  # ProxyType

    def __init__(self, synctx):
        self.synctx = obj_proxy(synctx)


class IncludePattern(SyntaxPattern):
    name: str

    @classmethod
    def from_dict(cls, synctx, data: Dict):
        p = cls(synctx)
        p.name = data.get("include")
        return p

    @property
    def context(self) -> "SyntaxContext":
        return self.synctx.syndef[self.name]


class MatchPattern(SyntaxPattern):
    # 匹配的正则表达式
    match: MatchRegex

    # 为匹配的文本附加的 scope
    scope: Optional[str]

    # `match` 的正则捕获分组，为不同分组赋予不同的 scope
    captures: Optional[Dict[int, str]]

    # 匹配到该 pattern 时的动作
    action: Optional[MatchAction]

    @classmethod
    def from_dict(cls, synctx, data: Dict) -> "MatchPattern":
        p = cls(synctx)

        p.match = MatchRegex.create(synctx.syndef, data["match"])
        p.scope = data.get("scope")
        p.captures = data.get("captures")
        p.setup_action(data)

        return p

    def setup_action(self, data: Dict):
        """
        setup action object
        """
        self.action = None

        def get_nested_ctx(action_data):
            return SyntaxContext.from_dict(self.synctx.syndef, action_data)

        push_data = data.get("push")
        if isinstance(push_data, str):
            self.action = PushAction(self, push_data)
        elif isinstance(push_data, list):
            self.action = PushAction(self, get_nested_ctx(push_data))

        set_data = data.get("set")
        if isinstance(set_data, str):
            self.action = SetAction(self, set_data)
        elif isinstance(set_data, list):
            self.action = SetAction(self, get_nested_ctx(set_data))

        if "pop" in data.keys() and data.get("pop") is True:
            self.action = PopAction()


class SyntaxContext(object):
    syndef: "SyntaxDefinition"  # ProxyType

    meta_scope: Optional[str]
    meta_content_scope: Optional[str]
    meta_include_prototype: bool
    clear_scopes: Union[int, bool]
    patterns: List[SyntaxPattern]

    def __init__(self, syndef: "SyntaxDefinition"):
        self.syndef = obj_proxy(syndef)

    @classmethod
    def from_dict(cls, syndef, data: List[Dict]):
        ctx = cls(syndef)

        # set defaults
        ctx.meta_scope = None
        ctx.meta_content_scope = None
        ctx.meta_include_prototype = True
        ctx.clear_scopes = False
        ctx.patterns = []

        for item in data:
            # TODO: 验证数据类型
            # meta patterns
            if "meta_scope" in item:
                ctx.meta_scope = item.get("meta_scope")
            elif "meta_content_scope" in item:
                ctx.meta_content_scope = item.get("meta_content_scope")
            elif "meta_include_prototype" in item:
                ctx.meta_include_prototype = item.get("meta_include_prototype")
            elif "clear_scopes" in item:
                ctx.clear_scopes = item.get("clear_scopes")
            # include patterns
            elif "include" in item:
                ctx.patterns.append(IncludePattern.from_dict(ctx, item))
            elif "match" in item:
                ctx.patterns.append(MatchPattern.from_dict(ctx, item))
            else:
                raise ValueError  # FIXME

        return ctx

    def __getitem__(self, index: int):
        return self.patterns[index]


class SyntaxDefinition(object):
    name: str
    file_extensions: List[str]
    first_line_match: Optional[MatchRegex]

    scope: Optional[str]

    variables: Dict[str, str]
    contexts: List[SyntaxContext]

    # mapping from context name to index
    _context_names: Dict[str, int]

    @property
    def ctx_main(self) -> SyntaxContext:
        return obj_proxy(self["main"])

    @property
    def prototype_patterns(self) -> List[SyntaxPattern]:
        try:
            prototype_ctx = self["prototype"]
        except KeyError:  # no prototype
            return []
        return prototype_ctx.patterns

    @classmethod
    def load(cls, data: Dict):
        obj = cls()

        # TODO: validate data type
        obj.name = data.get("name")
        obj.file_extensions = data.get("file_extensions")
        obj.variables = data.get("variables", dict())
        obj.scope = data.get("scope")

        obj.first_line_match = MatchRegex.create(
            obj,
            data.get("first_line_match"),
        )

        # initial
        obj.contexts = list()
        obj._context_names = dict()
        obj._ctx_prototype = None
        obj._ctx_main = None

        # import contexts
        for ctx_name, ctx_data in data.get("contexts", {}).items():
            ctx = SyntaxContext.from_dict(obj, ctx_data)

            if ctx_name == "prototype":
                ctx.meta_include_prototype = False

            obj.contexts.append(ctx)
            ctx_index = len(obj.contexts) - 1
            obj._context_names[ctx_name] = ctx_index

        return obj

    def __getitem__(self, key: str) -> SyntaxContext:
        index = self._context_names[key]
        return self.contexts[index]
