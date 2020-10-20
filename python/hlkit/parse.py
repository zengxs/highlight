import re
from typing import List, Match, Optional, Tuple

from hlkit.syntax import (
    IncludePattern,
    MatchPattern,
    PopAction,
    PushAction,
    SetAction,
    SyntaxContext,
    SyntaxDefinition,
    SyntaxPattern,
    obj_proxy,
)


class ParseResult(object):
    """ 代码的解析结果 """

    tokens: List["Token"]

    class Token(object):
        text: str
        scopes: List[str]

        def __init__(self, text, scopes):
            self.text = text
            self.scopes = scopes

    def __init__(self, *tokens):
        self.tokens = list(tokens)

    def __len__(self) -> int:
        return len(self.tokens)

    @property
    def chars_count(self) -> int:
        # count for parsed characters
        return sum(map(lambda t: len(t.text), self.tokens))

    def extend(self, token_list: List[Token]):
        self.tokens.extend(token_list)


class StateLevel(object):
    current_ctx: SyntaxContext
    prototypes: List[SyntaxPattern]
    matches: List[MatchPattern]  # flatten `MatchPattern`

    def __init__(self, ctx):
        self.current_ctx = obj_proxy(ctx)
        self.matches = []

        if self.current_ctx.meta_include_prototype is True:
            proto_patterns = self.current_ctx.syndef.prototype_patterns
            proto_flattens = self._flatten_patterns(proto_patterns)
            self.matches.extend(proto_flattens)

        self.matches.extend(self._flatten_patterns(self.current_ctx.patterns))

    @staticmethod
    def _flatten_patterns(patterns: List[SyntaxPattern]) -> List[MatchPattern]:
        """ Get flatten `MatchPattern` list """
        result = []
        for pattern in patterns:
            if isinstance(pattern, MatchPattern):
                result.append(obj_proxy(pattern))
            elif isinstance(pattern, IncludePattern):
                pats = StateLevel._flatten_patterns(pattern.context.patterns)
                result.extend(pats)
            else:
                raise ValueError
        return result


class ParseState(object):
    syndef: SyntaxDefinition  # ProxyType
    level_stack: List["StateLevel"]

    def __init__(self, syndef: SyntaxDefinition):
        self.syndef = obj_proxy(syndef)
        self.level_stack = list()

        # push `main` context into `level_stack`
        self.push_context(self.syndef.ctx_main)

    def push_context(self, context: SyntaxContext):
        level = StateLevel(context)
        self.level_stack.append(level)

    def pop_context(self):
        self.level_stack.pop()

    def set_context(self, context: SyntaxContext):
        level = StateLevel(context)
        self.level_stack.pop()
        self.level_stack.append(level)

    @property
    def current_level(self) -> StateLevel:
        return self.level_stack[-1]

    @property
    def current_context(self) -> SyntaxContext:
        return self.current_level.current_ctx

    def current_scopes(self, *, with_meta_scope=True) -> List[str]:
        scopes = []

        if self.syndef.scope is not None:
            scopes.append(self.syndef.scope)

        for i in range(len(self.level_stack)):
            level = self.level_stack[i]
            is_not_last = i < len(self.level_stack) - 1

            # TODO: clear_scopes
            ctx = level.current_ctx

            if is_not_last or with_meta_scope:
                if ctx.meta_scope is not None:
                    scopes.append(ctx.meta_scope)

            if ctx.meta_content_scope is not None:
                scopes.append(ctx.meta_content_scope)

        return scopes

    def find_best_match(self, code) -> Tuple[MatchPattern, Match]:
        """
        找到最佳匹配的 MatchPattern 以及其正则匹配的结果
        """
        best_pattern: Optional[MatchPattern] = None
        best_match: Optional[Match] = None

        for pattern in self.current_level.matches:
            match = re.search(str(pattern.match), code)
            if match is None:
                continue

            if match.start() == 0:
                return pattern, match
            elif best_match is None:
                best_pattern = pattern
                best_match = match
            elif match.start() < best_match.start():
                best_pattern = pattern
                best_match = match
            else:
                continue

        return best_pattern, best_match

    def parse_next_token(self, line, start=0) -> ParseResult:
        snippet: str = line[start:]
        pattern, match = self.find_best_match(snippet)

        result = ParseResult()

        scopes = self.current_scopes()

        if pattern is None:
            token = ParseResult.Token(line[start:], scopes.copy())
            result.tokens.append(token)
            return result

        snippet = snippet[: match.end()]

        # 未匹配的文本赋予默认 scopes
        if match.start() > 0:
            text = snippet[: match.start()]
            token = ParseResult.Token(text, scopes.copy())
            result.tokens.append(token)

        # execute action
        if isinstance(pattern.action, PushAction):
            ctx = pattern.action.context
            self.push_context(ctx)
            if ctx.meta_scope is not None:
                scopes.append(ctx.meta_scope)

        elif isinstance(pattern.action, SetAction):
            ctx = pattern.action.context
            self.set_context(ctx)
            scopes = self.current_scopes()

        elif isinstance(pattern.action, PopAction):
            # exclude meta_scope of current level
            scopes = self.current_scopes(with_meta_scope=False)
            self.pop_context()

        # pattern scope
        if pattern.scope is not None:
            scopes.append(pattern.scope)

        # execute captures
        if pattern.captures is None:
            token = ParseResult.Token(snippet[match.start():], scopes.copy())
            result.tokens.append(token)
            return result

        pos = match.start()
        for group_no in sorted(pattern.captures.keys()):
            if group_no > len(match.groups()):
                continue

            start, end = match.span(group_no)
            if start == end:  # skip empty group
                continue
            if start > pos:  # 非分组文本
                text = snippet[pos:start]
                token = ParseResult.Token(text, scopes.copy())
                result.tokens.append(token)

            # 分组文本
            text = snippet[start:end]
            addition_scope = pattern.captures[group_no]
            token = ParseResult.Token(text, scopes + [addition_scope])
            result.tokens.append(token)

            pos = end

        text = snippet[pos:]  # 捕获剩下的文本
        if len(text) > 0:
            token = ParseResult.Token(text, scopes)
            result.tokens.append(token)

        return result

    def parse_line(self, line: str) -> ParseResult:
        final_result = ParseResult()
        pos = 0

        while pos < len(line):
            result = self.parse_next_token(line, pos)
            final_result.extend(result.tokens)
            pos += result.chars_count

        return final_result
