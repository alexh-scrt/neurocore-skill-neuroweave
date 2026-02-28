"""Sphinx configuration for neurocore-skill-neuroweave."""

project = "neurocore-skill-neuroweave"
author = "NeuroCore Contributors"
release = "0.1.0"

extensions = [
    "autoapi.extension",
]

autoapi_dirs = ["../src"]
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]
autoapi_ignore = ["*/__pycache__/*"]

html_theme = "furo"
html_title = "neurocore-skill-neuroweave"
