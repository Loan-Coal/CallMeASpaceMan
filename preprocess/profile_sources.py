"""Step 1 — profile the raw sources before making any modeling decision.

Usage:  .venv/Scripts/python preprocess/profile_sources.py

For every CSV under data/raw/{coursera,esco}/ it prints: size, columns, missing values,
duplicate rows, and a few sample values. For Coursera it also inspects the skills
column, because that column is our join key with ESCO and its format decides the
pre-processing (is it a list? what separator? how many skills per course?).

Nothing is modified: this script only reads.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
SOURCES = ("coursera", "esco")
SKILL_COLUMN_HINTS = ("skill_gain", "skills", "skill")
CANDIDATE_ID_HINTS = ("url", "link", "id", "slug")
SAMPLE_SIZE = 3


def read_csv(path: Path) -> pd.DataFrame:
    """Read everything as text: profiling must not silently convert types."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8")


def profile_table(name: str, df: pd.DataFrame) -> None:
    print(f"\n=== {name}: {len(df):,} rows x {len(df.columns)} cols")
    print(f"duplicate rows: {df.duplicated().sum():,}")
    missing = df.isna().mean().mul(100).round(1)
    for col in df.columns:
        samples = df[col].dropna().head(SAMPLE_SIZE).tolist()
        shown = [s[:60] + ("…" if len(s) > 60 else "") for s in samples]
        print(f"  - {col:<35} missing {missing[col]:>5}%  distinct {df[col].nunique():>7,}  e.g. {shown}")


def find_column(df: pd.DataFrame, hints: tuple[str, ...]) -> list[str]:
    return [c for c in df.columns if any(h in c.lower() for h in hints)]


def parse_skill_cell(cell: str) -> list[str]:
    """Skills may be stored as a Python-list string "['A', 'B']" or as plain 'A, B'. Try both."""
    text = cell.strip()
    if text.startswith("["):
        try:
            value = ast.literal_eval(text)
            return [str(v).strip() for v in value if str(v).strip()]
        except (ValueError, SyntaxError):
            pass  # fall through to the plain-separator split below
    return [part.strip() for part in text.split(",") if part.strip()]


def profile_skills(df: pd.DataFrame, column: str) -> None:
    cells = df[column].dropna()
    lists = cells.map(parse_skill_cell)
    flat = pd.Series([s for skills in lists for s in skills], dtype=str)
    print(f"\n--- skills column '{column}'")
    print(f"courses with skills: {len(cells):,} / {len(df):,}")
    print(f"skills per course: mean {lists.map(len).mean():.1f}, max {lists.map(len).max()}")
    print(f"skill mentions: {len(flat):,}, distinct raw: {flat.nunique():,}, "
          f"distinct lowercased: {flat.str.lower().nunique():,}")
    print("raw cell examples:", cells.head(SAMPLE_SIZE).tolist())
    print("top 15 skills:\n" + flat.value_counts().head(15).to_string())
    top100_share = flat.value_counts().head(100).sum() / max(len(flat), 1) * 100
    print(f"share of mentions covered by the 100 most frequent skills: {top100_share:.0f}%")


def profile_identity(df: pd.DataFrame) -> None:
    """Is there a stable, unique key for a course? Drives the IRI strategy (D6)."""
    print("\n--- course identity candidates")
    for col in find_column(df, CANDIDATE_ID_HINTS) + find_column(df, ("title",)):
        print(f"  {col}: unique {df[col].nunique():,} / non-null {df[col].notna().sum():,}")


def main() -> None:
    for source in SOURCES:
        files = sorted((RAW / source).glob("*.csv"))
        if not files:
            print(f"[{source}] no CSV found in {RAW / source} — see data/raw/README.md")
            continue
        for path in files:
            try:
                df = read_csv(path)
            except (UnicodeDecodeError, pd.errors.ParserError) as err:
                print(f"[{source}] cannot read {path.name}: {err}")
                continue
            profile_table(f"{source}/{path.name}", df)
            if source == "coursera":
                for col in find_column(df, SKILL_COLUMN_HINTS):
                    profile_skills(df, col)
                profile_identity(df)


if __name__ == "__main__":
    main()
