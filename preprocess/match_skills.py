"""Step C — measure how Coursera skills align with ESCO (the decision gate).

Usage:  .venv/Scripts/python preprocess/match_skills.py [--threshold 90]

Matching policy ("precision grows with specificity"):
- exact   : normalized Coursera skill == normalized ESCO skill pref/alt label  -> link to the specific ESCO skill.
            (In the RDF this link is produced by the RML join J2, not by this script;
             the count printed here is the oracle the join must reproduce.)
- group   : otherwise, fuzzy match (rapidfuzz WRatio >= threshold) against ESCO *skill-group* labels
            -> a weak "same area" link. A wrong guess on a broad group costs little.
- none    : kept as our own skill concept.
Writes data/clean/course_skill.csv back with: exact_uris, group_uri, group_label, group_score.
Prints coverage + random sample pairs to check by hand.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from textnorm import normalize

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SAMPLE = 20
SEED = 7


def load_esco() -> tuple[dict[str, list[str]], dict[str, str], dict[str, str]]:
    esco = json.loads((CLEAN / "esco_en.json").read_text(encoding="utf-8"))
    exact: dict[str, list[str]] = {}
    for row in esco["skillLabels"]:
        exact.setdefault(row["norm"], []).append(row["uri"])
    group_by_norm = {normalize(g["label"]): g["uri"] for g in esco["groups"]}
    labels = {s["uri"]: s["label"] for s in esco["skills"]} | {g["uri"]: g["label"] for g in esco["groups"]}
    return exact, group_by_norm, labels


def match_distinct(norms: pd.Series, exact: dict, groups: dict, threshold: int) -> pd.DataFrame:
    rows = []
    group_choices = list(groups)
    for norm in norms.unique():
        uris = exact.get(norm, [])
        hit = None if uris else process.extractOne(norm, group_choices, scorer=fuzz.WRatio, score_cutoff=threshold)
        rows.append({
            "norm_skill": norm,
            "exact_uris": " ".join(uris),
            "group_uri": groups[hit[0]] if hit else "",
            "group_label": hit[0] if hit else "",
            "group_score": round(hit[1]) if hit else "",
        })
    return pd.DataFrame(rows)


def match_type(row: pd.Series) -> str:
    return "exact" if row["exact_uris"] else "group" if row["group_uri"] else "none"


def report(cs: pd.DataFrame, labels: dict) -> None:
    cs = cs.assign(match=cs.apply(match_type, axis=1))
    distinct = cs.drop_duplicates("norm_skill")
    print("\n=== coverage")
    for name, frame in (("course-skill mentions", cs), ("distinct skills", distinct)):
        shares = frame["match"].value_counts(normalize=True).mul(100).round(1).to_dict()
        print(f"{name:<22} n={len(frame):>6,}  {shares}")
    linked = cs[cs["match"] != "none"].drop_duplicates(["kind", "name"])
    exact_courses = cs[cs["match"] == "exact"].drop_duplicates(["kind", "name"])
    print(f"courses with >=1 exact ESCO skill: {len(exact_courses):,}; with >=1 exact-or-group: {len(linked):,}")
    ambiguous = distinct[distinct["exact_uris"].str.contains(" ")]
    print(f"distinct skills matching >1 ESCO skill (ambiguous): {len(ambiguous):,}")
    print(f"J2 oracle — expected exact links (course, ESCO skill): {cs['exact_uris'].str.split().str.len().fillna(0).sum():,.0f}")
    print("\ntop 15 unmatched:", cs[cs["match"] == "none"]["raw_skill"].value_counts().head(15).to_dict())
    for kind in ("exact", "group"):
        sample = distinct[distinct["match"] == kind].sample(min(SAMPLE, (distinct["match"] == kind).sum()), random_state=SEED)
        print(f"\n=== {len(sample)} random {kind} pairs  (coursera  ->  ESCO)")
        for _, r in sample.iterrows():
            target = labels[r["exact_uris"].split()[0]] if kind == "exact" else f"{r['group_label']}  [{r['group_score']}]"
            print(f"  {r['norm_skill']:<40} -> {target}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=90)
    args = parser.parse_args()
    exact, groups, labels = load_esco()
    cs = pd.read_csv(CLEAN / "course_skill.csv", dtype=str, keep_default_na=False)
    cs = cs[["kind", "name", "raw_skill", "norm_skill", "skill_slug"]]
    matched = match_distinct(cs["norm_skill"], exact, groups, args.threshold)
    cs = cs.merge(matched, on="norm_skill", how="left")
    cs.to_csv(CLEAN / "course_skill.csv", index=False)
    print(f"fuzzy threshold: {args.threshold}")
    report(cs, labels)


if __name__ == "__main__":
    main()
