"""Skill-name normalization shared by BOTH sources.

The RML join J2 compares Coursera's `norm_skill` with ESCO's `norm` as plain strings,
so the two sides must be normalized by the exact same function — hence one module.

Kept deliberately minimal (each rule is a report line):
- lowercase, trim, collapse whitespace       -> "Data  Analysis " == "data analysis"
- "&" -> "and"                               -> "Research & Design" == "research and design"
- drop surrounding sentence punctuation      -> "SQL." == "sql"  (but "C++" / "C#" are kept intact)
No singularization: naive suffix stripping breaks words ("analysis" -> "analysi").
"""

from __future__ import annotations

import re

_SPACES = re.compile(r"\s+")
_EDGE_PUNCT = re.compile(r"""^[\s.,;:!?"'()\[\]-]+|[\s.,;:!?"'()\[\]-]+$""")


def normalize(label: str) -> str:
    text = label.lower().replace("&", " and ")
    text = _SPACES.sub(" ", text).strip()
    return _EDGE_PUNCT.sub("", text)


def slugify(label: str) -> str:
    """IRI-safe local name for our own skill concepts: 'Data Analysis' -> 'data-analysis'."""
    return re.sub(r"[^a-z0-9]+", "-", normalize(label)).strip("-")
