import os
from pathlib import Path

import pytest
import yaml
from hlkit.syntax import SyntaxDefinition

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
