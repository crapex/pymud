# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
#import sphinx_rtd_theme, sphinx_book_theme, sphinxawesome_theme, sphinx_nefertiti, piccolo_theme
import recommonmark, os, sys
from recommonmark.parser import CommonMarkParser
from recommonmark.transform import AutoStructify

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(r'../../src'))

source_parsers = {
    '.md': CommonMarkParser,
}
source_suffix = ['.rst', '.md']

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'PyMUD 帮助文档'
copyright = '2023-2024, crapex@crapex.cc'
author = 'crapex'
release = '0.20.2'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['recommonmark', 'sphinx_markdown_tables', 'sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.viewcode']

templates_path = ['_templates']
exclude_patterns = []

language = 'zh_CN'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
# sphinx_bootstrap_theme  sphinx_rtd_theme sphinx_nefertiti

html_theme = 'piccolo_theme'
html_static_path = ['css']
html_css_files = ['custom.css']
