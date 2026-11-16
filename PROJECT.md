# Data Integration Project — Working Notes

Course: "Lifting Data to RDF" — Franck Michel (Université Côte d'Azur / CNRS / Inria / I3S).
Solo project. **Priority: learning the concepts, not just shipping the deliverables.**

This file is the shared understanding between me and Claude. It tracks:
1. what the project asks for,
2. the decisions I have to make (each one brainstormed together, then recorded),
3. the concepts I need to understand along the way (there is a hand-written test).

Status legend: `OPEN` (not discussed) · `DISCUSSING` · `DECIDED` (with rationale)

---

## 1. What the project asks for

### Mission 1: choose the data
- Find a use case that integrates **2 data sources** (to study correlations, make recommendations, ...). Any topic.
- The sources must **exist**, be **independent**, contain **real-world data**, and be reachable as a local dump or over HTTP (Web API).
- Formats: CSV / JSON / XML.
- Pre-process if needed: remove outliers and missing values, and harmonize syntactic variations (location names, units, languages).

### Mission 2: lift the data to RDF and query it
- Translate both sources to RDF with **RML** and run them with **RMLMapper**.
  - Choose target vocabularies (Schema.org, DBpedia, LOV, ...).
  - Define a resource naming (IRI) strategy.
  - Write an **example of the RDF to generate**, by hand, before writing the mapping.
  - Define **how to join** the 2 sources (identifier? name? coordinates?).
- Run the mappings and host the result in a triple store (Corese, GraphDB, ...).
- Write **3 competency questions** that show the integration of the 2 sources and cover different parts of the graph.
- Write the equivalent SPARQL queries and verify their results.

### Mission 3: query the graph in natural language with an LLM
- Prototype a translation from a natural-language question to SPARQL, using any LLM.
- **"The important is the method, not the results."**
- Run the 3 competency questions through the prototype.
- Discuss what works, what doesn't and why, and what could be improved.

### What to submit
- **Zip**: mapping file(s), RDF result file(s), code.
- **Report**:
  - the scenario (sources and how they are joined)
  - the pre-processing, justified: which difficulties it addresses
  - the RDF modeling choices, justified: vocabularies and IRI strategy
  - the 3 competency questions, and why they are interesting
  - the 3 SPARQL queries, with screenshots of their execution
  - the NL→SPARQL choices, justified, and a discussion of the results
- **"No GenAI fluff!"** The report is written by me, in my own words.

### Schedule
| Date | Content |
|---|---|
| 16/11 | Data integration intro, R2RML & RML, hands-on |
| 23/11 | Advanced RML (joins, functions?), hands-on |
| 30/11 | Hands-on, then **hand-written test 11h00–12h15** |

---

## 2. Tooling (from the hands-on slides)
- **RMLMapper** v8.1.0 (jar, needs **Java ≥ 21**) or Docker image `rmlio/rmlmapper-java`.
  - `java -jar rmlmapper.jar -m mapping.ttl -o output.ttl -s turtle`
  - or with a config file: `--configfile rml.properties`
- Known pain points (per the teacher): outdated docs (the **test cases** in the rmlmapper-java repo are the most up-to-date reference), poor error messages, and confusion between RML and "RML2" namespaces.
- **Verified locally (16/11):** `tools/rmlmapper.jar` (8.1.0-r380) runs on Java 21. Two gotchas:
  - Mapping files **must declare `@base`**, otherwise `<#TriplesMap>` fails with "Not a valid (absolute) IRI".
  - Legacy `rml:`/`ql:` mappings are accepted and translated internally to the new `http://w3id.org/rml/` namespace (you see it in the output prefixes).
- VS Code extensions: Mentor, Stardog RDF Grammars, Linked Data Extension.
- Triple store / SPARQL: Corese (GUI), GraphDB, YasGUI.
- Examples: https://rml.io/docs/rml/examples/ and `rmlmapper-java/src/test/resources`.

---

## 3. Decisions to make

Each decision is brainstormed before it is recorded. For each one, fill in: options considered, choice, **why**, and what I learned. The "why" becomes the report.

### D1. Topic and use case — `DECIDED`
**Recommend Coursera courses for a desired job.** Coursera courses × ESCO (occupation → essential/optional skills). The join is on **skill labels** (free text, no shared ID), so it needs an alignment onto ESCO skill IRIs.
Why ESCO over O*NET: it's an existing, widely used vocabulary with stable IRIs to reuse; essential vs optional skills stand in for "which skills actually matter"; it has hierarchies for jobs and skills. O*NET is the fallback if the skill match rate is too low.
Original idea included jobs "gotten / refused" per skill set. Public hiring-outcome data is scarce (privacy). The only candidate found is the Akkodis/AEQUITAS anonymized hiring dataset. Its Zenodo record (14194204) is **restricted** (request access); if that doesn't come through, drop the outcome angle.
Coursera source chosen: Kaggle `elvinrustam/coursera-dataset`, about 9.6k rows, clean and unclean CSVs, with a `skill_gain` skills column (column list seen on a mirror; to verify after download).
Earlier ideas (not decided):
- **EV charging stations (IRVE, data.gouv) × electric vehicles registered per commune (SDES)**. Join on the INSEE commune code. Use case: under-equipped communes.
- **Nobel laureates API × World Bank indicators**. Join on country code. Use case: R&D spending vs. laureates.
- **Open Repair Alliance repair events × iFixit API**. Join on product category, which has no shared ID and needs an alignment. Closest to the course's "RePair" scenario.
- Open Food Facts × Agribalyse. ⚠ Probably not independent: OFF already uses Agribalyse internally.

Questions to think about: Which topic actually interests me? Which one has a clean join key? Which one gives interesting modeling work (code lists, hierarchies, links)?

### D2. Concrete sources and access method — `OPEN`
Exact datasets, URLs, formats, licenses, size. Dump or API? Do I subset the data, and how?
To check: do they really exist and download? Are they independent? How many rows? What encoding and delimiter?

### D3. Join strategy — `OPEN`
- Join key: an identifier, a name (fuzzy), coordinates?
- Mechanism: (a) both mappings generate the **same IRI** for the shared entity, so the graphs merge "by construction"; or (b) an explicit RML join (`rr:parentTriplesMap` + `rr:joinCondition`); or (c) linking after the fact (`owl:sameAs`).
- To learn: the trade-offs (performance, robustness, what happens when keys don't match).

### D4. Pre-processing — `OPEN`
What cleaning does each source need, and why? Tool (Python/pandas?). What belongs in pre-processing and what belongs in the mapping (FnO functions)?
To learn: where transformation logic *should* live (slides 26–28: SQL query vs. coined URIs + `owl:sameAs` vs. FnO vs. pre-processing).

### D5. Vocabularies / ontologies — `OPEN`
Which existing vocabularies (Schema.org, the INSEE geo ontology, SKOS, Wikidata/DBpedia, LOV, ...)? When is it justified to invent a term?
To learn: how to read an ontology's documentation (domain, range, the "concept in scheme" style of range seen with NORIA-O).

### D6. IRI naming strategy — `OPEN`
Base namespace, pattern per entity type, separating instances from vocabulary, stability and uniqueness of keys.
To learn: what makes a good IRI, and why "make URIs rather than literals".

### D7. Target RDF example — `OPEN`
Hand-written Turtle for 1–2 records of each source, written **before** the mapping. It doubles as the test oracle for the mapping output.

### D8. RML mapping design — `OPEN`
Triples maps per entity, logical sources, iterators (JSONPath/XPath), templates vs. references vs. constants, datatypes, language tags, joins.
Decide: legacy RML namespaces (`rml: <http://semweb.mmlab.be/ns/rml#>`, `ql:`, as in the slides) vs. RML2. Default: legacy, consistent with the course.

### D9. Triple store — `DECIDED`: Corese
GUI for screenshots, plus corese-server for the HTTP SPARQL endpoint that Mission 3 needs. Built by the teacher's own lab (Wimmics).

### D10. Competency questions + SPARQL — `OPEN`
Three questions that each need **both** sources and cover **different parts** of the graph (e.g. an aggregation across the join, a filter on a concept/IRI property, a traversal of a hierarchy or link). Each needs a gold SPARQL query and its expected results.

### D11. NL→SPARQL method — `OPEN`
Which LLM? What does the prompt contain (schema extracted from the graph? few-shot examples? entity linking? an execute-and-repair loop)? How are results evaluated (comparison against the gold queries)?
Idea: build it incrementally (zero-shot → +schema → +examples → +entity linking → +self-repair) and compare the steps. That gives a "method" story for the report.

### D12. Repo layout & workflow — `DECIDED`
`data/raw` (git-ignored), `data/clean`, `preprocess/`, `model/`, `mappings/`, `output/`, `queries/`, `nl2sparql/`, `report/`, `tools/` (jars, git-ignored).
The GitHub repo is **public**, so raw data (Kaggle/ESCO licences) and the course PDFs stay out of git. `data/raw/README.md` says how to download them.

---

## 4. Concepts to master (for the test and the report)

Check each off once I can explain it without notes.

- [ ] Data integration life cycle: discover → access → cleanse → model → transform → link → host → query
- [ ] Structural vs. semantic heterogeneity
- [ ] W3C Direct Mapping: table→class, row→resource, column→property, cell→object; its benefits and limits
- [ ] R2RML: TriplesMap, LogicalTable (tableName / sqlQuery), SubjectMap, PredicateObjectMap, ObjectMap
- [ ] Term maps: exactly one of `rr:column`/`rml:reference`, `rr:template`, `rr:constant`
- [ ] Shortcuts: `rr:class`, and `rr:subject`/`rr:predicate`/`rr:object`/`rr:graph` as constant maps; implicit typing
- [ ] Predicate-object maps: the Cartesian product of predicates × objects
- [ ] RML: LogicalSource, `rml:source`, `rml:referenceFormulation` (ql:CSV, ql:JSONPath, ql:XPath), `rml:iterator`
- [ ] The document-based iteration model (default iterators `$.*`, `/*`)
- [ ] Datatypes and language tags on object maps
- [ ] Joins between triples maps (`rr:parentTriplesMap`, `rr:joinCondition`), expected on 23/11
- [ ] Mapping values to controlled vocabularies (SKOS concepts): pre-processing vs. FnO vs. `owl:sameAs`
- [ ] FnO (functions in mappings), expected on 23/11
- [ ] SPARQL: basic graph patterns, OPTIONAL, FILTER, aggregates / GROUP BY, federated SERVICE

---

## 5. Decision log

(Filled in as decisions are made: date, decision, rationale, alternatives rejected.)

- **16/11 — Working mode: mixed.** I write the conceptual parts (hand-written Turtle, CQs, report). Claude drafts the code (pre-processing, NL→SPARQL) and explains it; I review and own it.
- **16/11 — LLM for Mission 3:** Claude (via Claude Code) first, Ollama as the local fallback.
- **16/11 — Report:** English, short (about 2 pages plus figures and screenshots). Only choices, reasons and evidence. No re-explaining course concepts.
- **16/11 — Topic:** Coursera (Kaggle `elvinrustam/coursera-dataset`) × ESCO (English, CSV, full dataset, no domain subset). See D1.
- **16/11 — Skill matching (to validate at the step-2 checkpoint):** exact match (after normalization) at the specific-skill level, fuzzy only at the skill-group level. Rationale: the precision you need grows with how specific the skill is. Unmatched Coursera skills are kept as our own SKOS concepts.
- **16/11 — Who writes what:** Claude drafts the RML mappings and gold SPARQL with every part explained; I rework them and own them. Before running each mapping, I predict the output of 2–3 of its parts (test practice). I write the hand-written Turtle, the CQ wording and the report.
- **16/11 — Deadline:** 30/11 (same day as the written test).

## 6. Open questions for the teacher

- (none yet)
