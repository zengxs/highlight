import os
from pathlib import Path

import yaml
from hlkit.syntax import MatchPattern, SyntaxDefinition
from hlkit.parse import ParseResult, ParseState

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ASSETS_DIR = os.path.abspath(ASSETS_DIR)


class TestParseState(object):
    syndef: SyntaxDefinition

    def setup_method(self, method):
        synfile = "Packages/JSON/JSON.sublime-syntax"
        full_path = Path(os.path.join(ASSETS_DIR, synfile))
        data = yaml.load(full_path.read_text(), yaml.FullLoader)
        self.syndef = SyntaxDefinition.load(data)

    def test_flatten(self):
        state = ParseState(self.syndef)

        # MatchPatterns in main context:
        # - comments[*] | prototype | 3
        # - constant[*] | main -> value -> constant | 1
        # - number[*] | main -> value -> number | 2
        # - string[*] | main -> value -> string | 1
        # - array[*] | main -> value -> array | 1
        # - object[*] | main -> value -> object | 1
        matches = state.current_level.matches

        assert len(matches) == 9

        # comments[0]
        assert matches[0].match._regex == r"/\*\*(?!/)"
        # constant[0]
        assert matches[3].match._regex == r"\b(?:true|false|null)\b"
        # number[1]
        assert matches[5].match._regex == r"(-?)(0|[1-9]\d*)"
        # string[0]
        assert matches[6].match._regex == r'"'
        # array[0]
        assert matches[7].match._regex == r"\["
        # object[0]
        assert matches[8].match._regex == r"\{"

    def test_best_match(self):
        state = ParseState(self.syndef)

        pattern, match = state.find_best_match(" [ \n")
        assert isinstance(pattern, MatchPattern)
        assert pattern.scope == "punctuation.section.sequence.begin.json"
        assert match.start() == 1

        pattern, match = state.find_best_match(" \n")
        assert pattern is None
        assert match is None

        pattern, match = state.find_best_match(r'"\n"')
        assert pattern.match._regex == r'"'  # string[0]
        assert pattern.scope == "punctuation.definition.string.begin.json"

        state.push_context(self.syndef["inside-string"])
        pattern, match = state.find_best_match(r"a\tc\n")
        assert pattern.scope == "constant.character.escape.json"
        assert match.group() == r"\t"

    def test_next_token(self):
        state = ParseState(self.syndef)

        line = " // comment\n"
        result = state.parse_next_token(line)

        assert isinstance(result, ParseResult)
        assert len(line) == result.chars_count
        assert len(result.tokens) == 3
        assert result.tokens[0].text == " "
        assert result.tokens[0].scopes == ["source.json"]
        assert result.tokens[1].text == "//"
        assert result.tokens[1].scopes == [
            "source.json",
            "comment.line.double-slash.js",
            "punctuation.definition.comment.json",
        ]
        assert result.tokens[2].text == " comment\n"
        assert result.tokens[2].scopes == [
            "source.json",
            "comment.line.double-slash.js",
        ]

    def test_next_token2(self):
        state = ParseState(self.syndef)
        line, pos = "[12,// comment\n", 0
        result = state.parse_next_token(line, start=pos)
        pos += result.chars_count
        assert pos == 1 and result.tokens[0].text == "["
        assert result.tokens[0].scopes == [
            "source.json",
            "meta.sequence.json",
            "punctuation.section.sequence.begin.json",
        ]
        result = state.parse_next_token(line, start=pos)
        pos += result.chars_count
        assert pos == 3 and result.tokens[0].text == "12"
        assert result.tokens[0].scopes == [
            "source.json",
            "meta.sequence.json",
            "meta.number.integer.decimal.json",
            "constant.numeric.value.json",
        ]
        result = state.parse_next_token(line, start=pos)
        pos += result.chars_count
        assert pos == 4 and result.tokens[0].text == ","
        assert result.tokens[0].scopes == [
            "source.json",
            "meta.sequence.json",
            "punctuation.separator.sequence.json",
        ]
        result = state.parse_next_token(line, start=pos)
        pos += result.chars_count
        assert pos == len(line)
        assert result.tokens[0].text == "//"
        assert result.tokens[0].scopes == [
            "source.json",
            "meta.sequence.json",
            "comment.line.double-slash.js",
            "punctuation.definition.comment.json",
        ]
        assert result.tokens[1].text == " comment\n"
        assert result.tokens[1].scopes == [
            "source.json",
            "meta.sequence.json",
            "comment.line.double-slash.js",
        ]

        line, pos = '  "a\\tb", ab\n', 0
        result = state.parse_next_token(line, start=pos)
        pos += result.chars_count
        assert pos == 3
        assert result.tokens[0].text == "  "
        assert result.tokens[1].text == '"'
        result = state.parse_next_token(line, start=pos)
        pos += result.chars_count
        assert pos == 6
        assert result.tokens[0].text == "a"
        assert result.tokens[1].text == r"\t"
        result = state.parse_next_token(line, start=pos)
        pos += result.chars_count
        assert pos == 8
        assert result.tokens[0].text == "b"
        assert result.tokens[1].text == '"'
        result = state.parse_next_token(line, start=pos)
        pos += result.chars_count
        assert pos == 9
        assert result.tokens[0].text == ","
        result = state.parse_next_token(line, start=pos)
        pos += result.chars_count
        assert pos == 11
        assert result.tokens[0].text == " "
        assert result.tokens[1].text == "a"
        assert result.tokens[1].scopes == [
            "source.json",
            "meta.sequence.json",
            "invalid.illegal.expected-sequence-separator.json",
        ]
        result = state.parse_next_token(line, start=pos)
        pos += result.chars_count
        assert result.tokens[0].text == "b"
        assert result.tokens[0].scopes == [
            "source.json",
            "meta.sequence.json",
            "invalid.illegal.expected-sequence-separator.json",
        ]
        result = state.parse_next_token(line, start=pos)
        pos += result.chars_count
        assert pos == len(line)
        assert result.tokens[0].text == "\n"
        assert result.tokens[0].scopes == [
            "source.json",
            "meta.sequence.json",
        ]

    def test_push_context(self):
        state = ParseState(self.syndef)

        line = "["
        result = state.parse_next_token(line)
        assert result.tokens[0].text == "["
        assert state.level_stack[-1].current_ctx.meta_scope == "meta.sequence.json"
