import os
from glob import glob
from pathlib import Path

from setuptools import setup

SRCROOT = os.path.dirname(__file__)

requires_path = Path(SRCROOT) / "python" / "requires" / "common.txt"
requires = requires_path.read_text().strip().splitlines()

setup(
    name="highlight-kit",
    version="0.1.0",
    description="Syntax highlighting using sublime syntax definitions",
    package_dir={"": "python"},
    packages=["hlkit"],
    python_requires=">=3.5",
    install_requires=requires,
    setup_requires=["cffi>=1.0.0"],
    cffi_modules=["python/onig_build.py:ffibuilder"],
    package_data={
        "hlkit": glob("assets/**/*.sublime-syntax", recursive=True),
    },
)
