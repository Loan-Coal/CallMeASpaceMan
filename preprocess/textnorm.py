"""Skill-name normalization shared by BOTH sources.

The RML join J2 compares Coursera's `norm_skill` with ESCO's `norm` as plain strings,
so the two sides must be normalized by the exact same function — hence one module.

Kept deliberately minimal (each rule is a report line):
- lowercase, trim, collapse whitespace       -> "Data  Analysis " == "data analysis"
- "&" -> "and"                               -> "Research & Design" == "research and design"
- drop surrounding sentence punctuation      -> "SQL." == "sql"  (but "C++", "C#", ".NET" are kept intact)
- drop parenthesised qualifiers              -> "Python (computer programming)" == "python", "Database (DBMS)" == "database"
- drop a trailing " programming"             -> "Python Programming" == "python", "R Programming" == "r"
  (gate 23/11: exact coverage of skill mentions 18.6% -> 21.4%; applied to both sides, so the
   ESCO label "computer programming" -> "computer" still matches Coursera's "Computer Programming")
No singularization: naive suffix stripping breaks words ("analysis" -> "analysi").
"""

from __future__ import annotations

import re

_SPACES = re.compile(r"\s+")
_PARENTHESES = re.compile(r"\([^)]*\)")
_LEADING_PUNCT = re.compile(r"""^[\s,;:!?"'()\[\]-]+""")  # no "." here: keeps ".net"
_TRAILING_PUNCT = re.compile(r"""[\s.,;:!?"'()\[\]-]+$""")
_TRAILING_PROGRAMMING = re.compile(r"(?<=\S) programming$")


def normalize(label: str) -> str:
    text = _PARENTHESES.sub(" ", label.lower()).replace("&", " and ")
    text = _SPACES.sub(" ", text).strip()
    text = _TRAILING_PUNCT.sub("", _LEADING_PUNCT.sub("", text))
    return _TRAILING_PROGRAMMING.sub("", text)


def slugify(label: str) -> str:
    """IRI-safe local name for our own skill concepts: 'Data Analysis' -> 'data-analysis'."""
    return re.sub(r"[^a-z0-9]+", "-", normalize(label)).strip("-")
