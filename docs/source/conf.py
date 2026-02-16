# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
# import sphinx_rtd_theme, sphinx_book_theme, sphinxawesome_theme, sphinx_nefertiti, piccolo_theme
import os
import sys
from importlib.metadata import version as get_version

from recommonmark.parser import CommonMarkParser

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(r"../../src"))

source_parsers = {
    ".md": CommonMarkParser,
}
source_suffix = [".rst", ".md"]

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "PyMUD"
copyright = "2023-2026, pymud.cn"
author = "crapex"
release = get_version("pymud")

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "recommonmark",
    "sphinx_markdown_tables",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_immaterial",
]

templates_path = ["_templates"]
exclude_patterns = []

language = "zh"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
# sphinx_bootstrap_theme  sphinx_rtd_theme sphinx_nefertiti


# html_theme = "piccolo_theme"

# html_permalinks_icon = "<span>#</span>"

#html_theme = "pymud"
#html_theme_path = ["../sphinx_theme"]

html_logo = "_static/icon.jpg"
html_theme = "sphinx_immaterial"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "repo_url": "https://github.com/crapex/pymud",
    "repo_name": "PyMUD",

    "icon": {
        "logo": "",
    },

    "features": [
        "navigation.expand",
        #"navigation.tabs",
        "navigation.sections",
        "toc.follow",
        "toc.sticky",
        "search.share",
    ],
    "social": [
        {
            "icon": "fontawesome/solid/house",
            "link": "https://www.pymud.cn",
            "name": "官方网站",
        },
        {
            "icon": "fontawesome/solid/comments",
            "link": "https://bbs.pymud.cn",
            "name": "官方论坛",
        },
    ]
}
