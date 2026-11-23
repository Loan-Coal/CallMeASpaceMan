"""Step B — clean the Coursera Kaggle CSV into two tidy CSVs for RML.

Usage:  .venv/Scripts/python preprocess/clean_coursera.py

Difficulties addressed (each one is a report line):
1. Same course repeated once per category (8,370 rows, 6,093 URLs) -> one row per URL, categories joined with "|".
2. "Not specified" used as a value       -> empty (= missing), so RML emits no triple for it.
3. Several skills in one cell ("A, B, C") -> one row per (course, skill) in course_skill.csv
   (RML cannot split a cell without FnO).
4. Duration in hours as a float           -> ISO 8601 duration "PT20H" (Schema.org timeRequired expects a Duration).
5. Level "Beginner level"                 -> code "beginner" (used in the level IRI).
6. Course URL -> (kind, name) = ("learn", "fashion-design"): the stable key of the course IRI.
   The dataset mixes 4 kinds (learn / specializations / projects / professional certificates) and the same
   name can exist under two kinds, so the name alone is NOT unique: the IRI uses {kind}/{name}.
   (Two separate columns: RML templates percent-encode a "/" inside a value.)
Outputs: data/clean/courses.csv, data/clean/course_skill.csv
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from textnorm import normalize, slugify

ROOT = Path(__file__).resolve().parent.parent
RAW_ZIP = ROOT / "data" / "raw" / "coursera" / "coursera-kaggle.zip"
MEMBER = "CourseraDataset-Clean.csv"
CLEAN = ROOT / "data" / "clean"
MISSING = "Not specified"
URL_PATTERN = r"^https://www\.coursera\.org/(?P<kind>[a-z-]+)/(?P<name>[A-Za-z0-9-]+)/?$"
KIND_CODES = {"learn": "course", "specializations": "specialization", "projects": "project",
              "professional-certificates": "professional-certificate",
              "professional-certificate": "professional-certificate"}

COLUMNS = {
    "Course Title": "title", "Rating": "rating", "Level": "level_raw", "Skill gain": "skills",
    "Offered By": "provider", "Keyword": "category", "Course Url": "url",
    "Duration to complete (Approx.)": "hours", "Number of Review": "reviews",
}


def load() -> pd.DataFrame:
    with zipfile.ZipFile(RAW_ZIP) as archive, archive.open(MEMBER) as handle:
        df = pd.read_csv(handle, dtype=str, keep_default_na=False)
    df = df[list(COLUMNS)].rename(columns=COLUMNS)
    return df.apply(lambda col: col.str.strip().replace(MISSING, ""))


def dedupe(df: pd.DataFrame) -> pd.DataFrame:
    """One row per course URL; the only column that differs between duplicates is the category."""
    categories = df.groupby("url")["category"].agg(lambda c: "|".join(sorted(set(filter(None, c)))))
    first = df.drop_duplicates("url").set_index("url").drop(columns="category")
    return first.join(categories).reset_index()


def iso_duration(hours: str) -> str:
    try:
        value = float(hours)
    except ValueError:
        return ""
    return f"PT{value:g}H" if value > 0 else ""


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    parts = df["url"].str.extract(URL_PATTERN)
    return df.assign(
        kind=parts["kind"].map(KIND_CODES),
        name=parts["name"],
        level=df["level_raw"].str.lower().str.removesuffix(" level"),
        duration=df["hours"].map(iso_duration),
        provider_slug=df["provider"].map(lambda p: slugify(p) if p else ""),
    )


def explode_skills(df: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {"kind": kind, "name": name, "raw_skill": raw, "norm_skill": normalize(raw), "skill_slug": slugify(raw)}
        for kind, name, cell in zip(df["kind"], df["name"], df["skills"])
        for raw in (s.strip() for s in cell.split(","))
        if raw and normalize(raw)
    ]
    return pd.DataFrame(rows).drop_duplicates(["kind", "name", "norm_skill"])


def check(df: pd.DataFrame) -> None:
    """Fail fast if an assumption about the data is wrong."""
    unknown = df[df["kind"].isna() | df["name"].isna()]
    if len(unknown):
        raise ValueError(f"{len(unknown)} URLs do not match the expected pattern, e.g. {unknown['url'].iloc[0]}")
    if df.duplicated(["kind", "name"]).any():
        raise ValueError("duplicate (kind, name) after dedupe")


def main() -> None:
    raw = load()
    courses = enrich(dedupe(raw))
    check(courses)
    skills = explode_skills(courses)
    CLEAN.mkdir(parents=True, exist_ok=True)
    keep = ["kind", "name", "title", "url", "provider", "provider_slug", "level", "rating", "reviews", "duration", "category"]
    courses[keep].to_csv(CLEAN / "courses.csv", index=False)
    skills.to_csv(CLEAN / "course_skill.csv", index=False)
    print(f"raw rows {len(raw):,} -> courses {len(courses):,}")
    print(f"courses without skills: {(courses['skills'] == '').sum():,}")
    print(f"kinds: {courses['kind'].value_counts().to_dict()}")
    print(f"levels: {courses['level'].replace('', '(missing)').value_counts().to_dict()}")
    print(f"course-skill rows: {len(skills):,}, distinct norm skills: {skills['norm_skill'].nunique():,}")


if __name__ == "__main__":
    main()
