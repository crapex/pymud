# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import recommonmark, sphinx_rtd_theme
from recommonmark.parser import CommonMarkParser
from recommonmark.transform import AutoStructify

source_parsers = {
    '.md': CommonMarkParser,
}
source_suffix = ['.rst', '.md']

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'pymud-cookbook'
copyright = '2024, crapex@crapex.cc'
author = 'crapex'
release = '0.18.4'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['recommonmark', 'sphinx_markdown_tables']

templates_path = ['_templates']
exclude_patterns = []

language = 'zh_CN'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# def setup(app):
#     app.add_config_value('recommonmark_config', {
#         'url_resolver': lambda url: github_doc_root + url,
#         'auto_toc_tree_section': 'Contents',
#         }, True)
#     app.add_transform(AutoStructify)