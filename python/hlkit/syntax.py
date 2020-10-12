from typing import Dict, Optional, Sequence, Union


class SyntaxMatchPattern(object):
    # 匹配的正则表达式
    match: str

    # 为匹配的文本附加的 scope
    scope: Optional[str]

    # `match` 的正则捕获分组，为不同分组赋予不同的 scope
    captures: Optional[Dict[int, str]]

    # 推出当前 context
    pop: Optional[bool]

    # `push` 是一个 context 的名字，用于将这个 context 推入栈中
    push: Optional[Union[str, "SyntaxContext"]]

    # `set` 是一个 context 的名字，作用与 `push` 类似，但是它会现将当前的 context 推出
    set: Optional[Union[str, "SyntaxContext"]]

    @classmethod
    def from_dict(cls, data: Dict) -> "SyntaxMatchPattern":
        p = cls()

        p.match = data.get("match")
        p.scope = data.get("scope")
        p.captures = data.get("captures")
        p.pop = data.get("pop", False)
        p.push = cls.ctx_name_or_nested(data.get("push"))
        p.set = cls.ctx_name_or_nested(data.get("set"))

        return p

    @staticmethod
    def ctx_name_or_nested(
        data: Optional[Union[str, Dict]],
    ) -> Optional[Union[str, "SyntaxContext"]]:
        """
        Get context name for push/set or nested context object
        """
        if data is None:
            return None
        if isinstance(data, str):
            return data
        if isinstance(data, list):
            return SyntaxContext.from_dict(data)

        raise ValueError(data)  # FIXME


class SyntaxIncludePattern(object):
    # 包含的 context 的名字
    name: str

    @classmethod
    def from_dict(cls, data: Dict):
        p = cls()

        p.name = data.get("include")

        return p


class SyntaxContext(object):
    meta_scope: str
    meta_content_scope: str
    meta_include_prototype: bool
    clear_scopes: Union[int, bool]

    patterns: Sequence[Union[SyntaxMatchPattern, SyntaxIncludePattern]]

    @classmethod
    def from_dict(cls, data: Sequence[Dict]):
        ctx = cls()
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
                ctx.patterns.append(SyntaxIncludePattern.from_dict(item))
            elif "match" in item:
                ctx.patterns.append(SyntaxMatchPattern.from_dict(item))
            else:
                raise ValueError  # FIXME

        return ctx


class SyntaxDefinition(object):
    name: str
    file_extensions: Sequence[str]
    scope: Optional[str]

    contexts: Sequence[SyntaxContext]

    # mapping from context name to index
    _context_names: Dict[str, int]

    # index of prototype context
    _ctx_prototype: Optional[int]

    # index of main context
    _ctx_main: int

    @classmethod
    def load(cls, data: Dict):
        obj = cls()

        # TODO: validate data type
        obj.name = data.get("name")
        obj.file_extensions = data.get("file_extensions")
        obj.scope = data.get("scope")

        # initial
        obj.contexts = list()
        obj._context_names = dict()
        obj._ctx_prototype = None
        obj._ctx_main = None

        # import contexts
        for ctx_name, ctx_data in data.get("contexts", {}).items():
            ctx = SyntaxContext.from_dict(ctx_data)
            obj.contexts.append(ctx)
            ctx_index = len(obj.contexts) - 1
            obj._context_names[ctx_name] = ctx_index

            if ctx_name == "main":
                obj._ctx_main = ctx_index
            if ctx_name == "prototype":
                obj._ctx_prototype = ctx_index

        return obj
