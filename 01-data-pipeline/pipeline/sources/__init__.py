"""Each source module has fetch(cfg, start, end) and a pure parse function.

fetch returns {table name: [row, ...]}. It saves the raw response first.
"""


class Skipped(Exception):
    """The source cannot run, for example because an API key is missing."""
