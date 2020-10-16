import os
from pathlib import Path

import pytest
import yaml
from hlkit.syntax import (
    IncludePattern,
    MatchPattern,
    MatchRegex,
    PopAction,
    PushAction,
    SyntaxDefinition,
)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ASSETS_DIR = os.path.abspath(ASSETS_DIR)


@pytest.mark.parametrize(
    "root, path",
    [
        (ASSETS_DIR, "Packages/JSON/JSON.sublime-syntax"),
        (ASSETS_DIR, "Packages/Graphviz/DOT.sublime-syntax"),
        (ASSETS_DIR, "Packages/YAML/YAML.sublime-syntax"),
    ],
)
def test_load(root, path):
    """
    :param root: root directory of syntax definitions
    :param path: `.sublime-syntax` file path. relative of `root`
    """
    fullpath = Path(os.path.join(root, path))

    data = yaml.load(fullpath.read_text(), yaml.FullLoader)

    SyntaxDefinition.load(data)


class TestStructure(object):
    root = ASSETS_DIR

    def _load(self, path):
        fullpath = Path(os.path.join(self.root, path))
        data = yaml.load(fullpath.read_text(), yaml.FullLoader)
        return SyntaxDefinition.load(data)

    def test_json(self):
        syndef = self._load("Packages/JSON/JSON.sublime-syntax")

        assert syndef.name == "JSON"
        assert syndef.scope == "source.json"
        assert len(syndef.contexts) == 11
        assert syndef._context_names["prototype"] == 0
        assert syndef._context_names["main"] == 1

        pat_0 = syndef["string"].patterns[0]
        assert isinstance(pat_0, MatchPattern)
        assert isinstance(pat_0.action, PushAction)
        assert pat_0.action._ctxname == "inside-string"

        action_ctx = pat_0.action.context
        assert action_ctx.meta_scope == "string.quoted.double.json"

        pat_1 = action_ctx.patterns[1]
        assert isinstance(pat_1, IncludePattern)
        assert pat_1.name == "string-escape"

        pat_2 = action_ctx.patterns[-1]
        assert isinstance(pat_2, MatchPattern)
        assert isinstance(pat_2.action, PopAction)

    def test_match_regex(self):
        syndef = self._load("Packages/YAML/YAML.sublime-syntax")

        assert isinstance(syndef.first_line_match, MatchRegex)
        assert str(syndef.first_line_match) == r"^%YAML( ?1.\d+)?"

        def expand_re(regex):
            return str(MatchRegex.create(syndef, regex))

        def expand_var(varname):
            regex = syndef.variables[varname]
            return expand_re(regex)

        assert expand_var("c_flow_indicator") == r"[\[\]{},]"
        assert expand_var("ns_word_char") == r"[0-9A-Za-z\-]"
        assert expand_var("c_tag_handle") == r"(?:!(?:[0-9A-Za-z\-]*!)?)"

        # fmt: off
        assert expand_re("{{_type_int_binary}}{{_flow_scalar_end_plain_out}}") == r"""([-+]?)(0b)([0-1_]+)(?x:
  (?=
      \s* $
    | \s+ \#
    | \s* : (\s|$)
  )
)"""
        # fmt: on

        assert (
            expand_re("{{_type_int_binary}}{{_type_int_binary}}")
            == r"([-+]?)(0b)([0-1_]+)([-+]?)(0b)([0-1_]+)"
        )
