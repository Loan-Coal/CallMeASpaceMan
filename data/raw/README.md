# Raw data (not committed)

Both sources are third-party data and are re-downloadable, so they are git-ignored.
The scripts read the archives directly (no manual unzip needed).

## Coursera — `data/raw/coursera/coursera-kaggle.zip`
- Kaggle: https://www.kaggle.com/datasets/elvinrustam/coursera-dataset (needs a Kaggle login)
- Contains `CourseraDataset-Clean.csv` (used) and `CourseraDataset-Unclean.csv` (not used).

## ESCO — `data/raw/esco/esco-v1.2.1-jsonld.zip`
- https://esco.ec.europa.eu/en/use-esco/download
- Version **v1.2.1** · Content: **classification** · Format: **JSON-LD** (one 656 MB file, all languages).
- We read it as plain JSON (format diversity: Coursera = CSV, ESCO = JSON); our RML builds our own model from it.
- The ESCO ontology (`model/esco-model.rdf`) is kept in the repo as a reading reference.
