# Claussant

A Claude Code skill and dataset collection for generating verified [Croissant](https://mlcommons.org/croissant/) metadata files for biomedical and life sciences datasets.

Claussant produces machine-readable dataset descriptors that conform to the [MLCommons Croissant 1.1 specification](https://docs.mlcommons.org/croissant/docs/croissant-spec-1.1.html) — with a strict guarantee: **every field in the output is traceable to a URL crawled during that session, never to the model's training knowledge.**

---

## What is Croissant?

Croissant is a JSON-LD metadata format for machine-learning datasets published by MLCommons. A Croissant file describes a dataset's identity, licensing, downloads, and schema in a standardised, machine-readable way — making it straightforward for ML frameworks, catalogues, and search engines to index and load datasets without manual documentation work.

---

## The `/robocroissant` Command

This repo ships a Claude Code slash command that generates a complete Croissant package for any publicly accessible dataset:

```
/robocroissant https://www.bindingdb.org
```

The command follows a strict three-phase pipeline:

### Phase 1 — Crawl and Inventory

Claude crawls the dataset's own domain top-down, starting from the homepage and following real links (never guessing URLs). It collects:

- Dataset identity: name, description, version, RRID, primary citation
- Licensing and access terms (verbatim, not paraphrased)
- Every downloadable file: URL, format, checksum

JavaScript-rendered sites (SPAs) are handled by fetching JS bundles directly and extracting route paths — no browser required.

### Phase 2 — Schema Extraction

For every file whose column names are not documented on a crawled page, Claude runs a partial download to extract the header row — without ever downloading the full file. Supported formats: TSV, CSV, ZIP-compressed TSV/CSV/SDF/MySQL, TAR, JSON.

Files behind authentication or CAPTCHA are marked `blocked` and deferred to the incomplete components file.

### Phase 3 — Write and Validate

Four output files are written into a versioned directory (`datasets/{name}/{version}/{run}/`):

| File | Purpose |
|------|---------|
| `{name}_croissant.json` | Verified Croissant metadata, mlcroissant-validated |
| `{name}_provenance.json` | Source URL for every claim in the Croissant file |
| `{name}_incomplete.json` | Components that could not be completed from public pages |
| `{name}_apis.json` | REST API and web tool documentation (not part of the Croissant spec) |

The structural validator (`mlcroissant validate`) is run automatically; every error is fixed before output is delivered. Key fields (`citeAs`, `license`, `name`, `description`) are re-fetched and compared character-by-character against the source page to catch any paraphrasing.

---

## Verification Guarantees

Claussant enforces two hard rules that distinguish it from naive LLM-based metadata generation:

**No training knowledge.** Every value in the Croissant file must be traceable to a URL fetched during that session. If a fact cannot be sourced, it is omitted from the Croissant file and recorded in the incomplete components file instead.

**Authoritative sources only.** All facts come from the dataset's own domain — not GitHub mirrors, community wikis, HuggingFace dataset cards, or third-party documentation. Web search is permitted only to discover real URLs on the authoritative domain.

---

## Datasets

| Dataset | Version | Description |
|---------|---------|-------------|
| [BindingDB](datasets/bindingdb/) | 202603 | Binding affinities for drug-target interactions |
| [CADRE](datasets/cadre/) | 2025-10-08 | Medicare claims data research environment |
| [CIViC](datasets/civic/) | 01-Mar-2026 | Clinical interpretation of variants in cancer |
| [HGNC](datasets/hgnc/) | 2026-03-06 | HUGO Gene Nomenclature Committee gene symbols |

Each dataset directory contains one subdirectory per version, and one subdirectory per run within that version. The highest-numbered run is the latest.

---

## Repository Structure

```
.claude/
  commands/
    robocroissant.md        # /robocroissant slash command
  skills/
    croissant/
      SKILL.md              # Full pipeline instructions for Claude
      references/
        fetch.py            # Phase 1: raw HTML fetcher and link extractor
        extract.py          # Phase 2: partial-download schema extractor
        nextver.py          # Determines next local version number
        check_provenance.py # Cross-checks provenance against Croissant file
        croissant-schema.md # Croissant JSON-LD schema reference
        provenance-format.md # Provenance file format specification
datasets/
  {name}/
    {dataset_version}/
      {run}/
        {name}_croissant.json
        {name}_provenance.json
        {name}_incomplete.json
        {name}_apis.json        # (if APIs exist)
```

---

## Usage

### Prerequisites

```bash
uv venv .venv
uv pip install --python .venv/bin/python mlcroissant requests
```

`requests` is needed by `fetch.py`. `mlcroissant` is needed for Phase 4 validation.

### Running

Open this repository in Claude Code and run:

```
/robocroissant https://example-dataset.org
```

Claude will crawl the site, extract schemas, write the four output files into `datasets/`, and validate the result — reporting what was completed and what ended up in the incomplete components file.

### Iterating

Each run is immutable. Corrections or additions always produce a new numbered run directory. To incorporate user-provided information (e.g. column headers from a downloaded file):

1. Share the content with Claude in the conversation
2. Run `/robocroissant` again — Claude will pick up the new `{local_version}` automatically

---

## Adding the Skill to Another Project

Copy `.claude/` into your project root. The skill and command will be available to Claude Code whenever you open that project. Update the `Base directory for this skill:` line in `robocroissant.md` to point to the absolute path of the `croissant` skill directory.

---

## Contributing

Contributions welcome — new datasets, fixes to existing Croissant files, and improvements to the skill pipeline. When adding a dataset, run the validator and provenance cross-check before opening a PR:

```bash
.venv/bin/mlcroissant validate --jsonld datasets/{name}/{version}/{run}/{name}_croissant.json
python3 .claude/skills/croissant/references/check_provenance.py \
  datasets/{name}/{version}/{run}/{name}_croissant.json \
  datasets/{name}/{version}/{run}/{name}_provenance.json
```
