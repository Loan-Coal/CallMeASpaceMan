"""Step A2 — reduce ESCO's JSON-LD dump to a small, regular, English-only JSON for RML.

Usage:  .venv/Scripts/python preprocess/extract_esco.py

We read the JSON-LD as *plain JSON* (we never interpret it as RDF): our RML mapping builds
our own model from it. Each fix below addresses a concrete difficulty of the raw file:
1. 656 MB in one document         -> too big for RMLMapper's in-memory JSONPath; keep only what we map.
2. 30 languages mixed              -> keep English (Coursera is English).
3. labels nested in SKOS-XL objects -> flatten `preferredLabel[].literalForm.en` to plain strings.
4. a field is a string OR a list    -> always a list, so one JSONPath (`field[*]`) works everywhere.
5. `type` arrays in random order    -> test membership, never position.
6. 318 obsolete skills              -> keep `status == released` only; drop links pointing to removed skills.
Output: data/clean/esco_en.json
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from textnorm import normalize

ROOT = Path(__file__).resolve().parent.parent
RAW_ZIP = ROOT / "data" / "raw" / "esco" / "esco-v1.2.1-jsonld.zip"
OUT = ROOT / "data" / "clean" / "esco_en.json"
LANG = "en"
GROUP_SCHEME = "http://data.europa.eu/esco/concept-scheme/skills-hierarchy"


def as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def labels(node: dict, field: str) -> list[str]:
    """English literal forms of SKOS-XL label objects (pref or alt)."""
    out = []
    for label in as_list(node.get(field)):
        if isinstance(label, dict):
            text = label.get("literalForm", {}).get(LANG)
            if text:
                out.append(text.strip())
    return sorted(set(out))


def load_graph(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        member = next(i for i in archive.infolist() if i.file_size > 0)
        with archive.open(member) as handle:
            return json.load(handle)["@graph"]


def kind(node: dict) -> str | None:
    types = as_list(node.get("type"))
    if "esco:Occupation" in types:
        return "occupation"
    if "esco:Skill" in types:
        return "skill"
    if types == ["skos:Concept"] and GROUP_SCHEME in as_list(node.get("inScheme")):
        return "group"
    return None


def is_released(node: dict) -> bool:
    return node.get("status") == "released"


def build(graph: list[dict]) -> dict[str, list[dict]]:
    by_kind: dict[str, list[dict]] = {"occupation": [], "skill": [], "group": []}
    for node in graph:
        k = kind(node)
        if k and is_released(node) and labels(node, "preferredLabel"):
            by_kind[k].append(node)

    skill_uris = {n["uri"] for n in by_kind["skill"]}
    hierarchy_uris = skill_uris | {n["uri"] for n in by_kind["group"]}

    def keep(uris: Any, allowed: set[str]) -> list[str]:
        return sorted(u for u in as_list(uris) if u in allowed)

    occupations = [
        {
            "uri": n["uri"],
            "label": labels(n, "preferredLabel")[0],
            "altLabels": labels(n, "alternativeLabel"),
            "essential": keep(n.get("relatedEssentialSkill"), skill_uris),
            "optional": keep(n.get("relatedOptionalSkill"), skill_uris),
        }
        for n in by_kind["occupation"]
    ]
    skills = [
        {
            "uri": n["uri"],
            "label": labels(n, "preferredLabel")[0],
            "altLabels": labels(n, "alternativeLabel"),
            "skillType": n.get("skillType", "").rsplit("/", 1)[-1],
            "broader": keep(n.get("broader"), hierarchy_uris),
        }
        for n in by_kind["skill"]
    ]
    groups = [
        {"uri": n["uri"], "label": labels(n, "preferredLabel")[0],
         "broader": keep(n.get("broader"), hierarchy_uris)}
        for n in by_kind["group"]
    ]
    return {"occupations": occupations, "skills": skills, "groups": groups,
            "skillLabels": skill_label_index(skills)}


def skill_label_index(skills: list[dict]) -> list[dict]:
    """Flat (uri, normalized label) pairs: the parent side of RML join J2."""
    pairs = {(s["uri"], normalize(lbl)) for s in skills for lbl in [s["label"], *s["altLabels"]]}
    return [{"uri": uri, "norm": norm} for uri, norm in sorted(pairs) if norm]


def main() -> None:
    graph = load_graph(RAW_ZIP)
    data = build(graph)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    links = sum(len(o["essential"]) + len(o["optional"]) for o in data["occupations"])
    print(f"input nodes: {len(graph):,}")
    for key, rows in data.items():
        print(f"{key:<12} {len(rows):>7,}")
    print(f"occupation->skill links: {links:,}")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
