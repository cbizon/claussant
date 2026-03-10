---
name: croissant
description: This skill should be used when the user asks to "create a Croissant file", "build a Croissant metadata file", "make a Croissant for a dataset", "generate a dataset descriptor", or provides a URL and asks to document a dataset in Croissant format. Also triggers when the user mentions "MLCommons Croissant", "dataset metadata", or "JSON-LD dataset description".
version: 1.0.0
---

# Croissant Dataset Metadata Generator

Produces a Croissant JSON-LD metadata file for a dataset, along with a companion provenance file that records the source URL for every claim made in the Croissant file, and an incomplete-components file for anything that could not be verified by crawling.

## Outputs

All output files are written into a versioned directory:

```
datasets/{name}/{dataset_version}/{local_version}/
```

- **`{name}`** — short lowercase slug for the dataset (e.g. `hgnc`, `bindingdb`)
- **`{dataset_version}`** — the value of the `version` field in the Croissant file (e.g. `202603`); use `unknown` if no version can be found before the directory must be created
- **`{local_version}`** — an integer (1, 2, 3, …) that increments with each new run; determine it by listing `datasets/{name}/{dataset_version}/` and taking one more than the highest existing integer subdirectory, or `1` if none exist

**To determine `{local_version}`**, run:
```bash
python3 $SKILL_REF/nextver.py datasets/{name}/{dataset_version}
```

Create the directory before writing any files:
```bash
mkdir -p datasets/{name}/{dataset_version}/{local_version}
```

The four output files inside that directory are:

1. **`{name}_croissant.json`** — verified Croissant metadata only; every field must be backed by a crawled source; must include `conformsTo`; must use only properties defined in `sc:`, `cr:`, and `dct:` namespaces
2. **`{name}_provenance.json`** — source URLs for every claim; see `references/provenance-format.md`
3. **`{name}_incomplete.json`** — Croissant components that could not be completed without downloading files or finding a data dictionary; omit this file only if everything was fully verified
4. **`{name}_apis.json`** — plain JSON documentation of REST APIs and web tools; omit if none exist; linked from the Croissant file via `relatedLink`

### Prior runs are off-limits

**Do not read, list the contents of, or reference files from any prior run directory** (`datasets/{name}/{dataset_version}/1/`, `datasets/{name}/{dataset_version}/2/`, etc.) unless the user explicitly says you may. You may list directory names to determine `{local_version}`, but that is the only permitted access to prior run paths.

## Verification Rule — No Training Knowledge

**Never use training knowledge to populate any field in the Croissant file.** Every value must be traceable to a URL fetched during the current session. If a fact cannot be sourced to a crawled page:

- **Omit it** from `{name}_croissant.json`
- **Record it** in `{name}_incomplete.json` with a note explaining what would be needed to complete it

This applies to everything: field names, data types, record counts, license versions, column descriptions, API parameters. When in doubt, leave it out and document it as incomplete.

## Authoritative Source Rule — No External Third-Party Sources

**All facts must come exclusively from the dataset's own domain.** Do not fetch, search, or cite pages from external sites (GitHub repositories, third-party documentation, community wikis, papers about the dataset, HuggingFace dataset cards, etc.) to populate any field. Such sources are created by others, may be wrong, outdated, or incomplete, and are not authoritative.

- **Allowed**: pages on the dataset's own domain (e.g. `bindingdb.org`), files served directly by that domain, and official API responses from that domain
- **Not allowed**: GitHub repos that process or mirror the data, community notebooks, third-party schema descriptions, papers describing the dataset (unless the dataset site itself links to them as the citation)

Web search (`site:example.org`) is permitted only to discover real URLs on the authoritative domain — not to find facts from external sources. If a web search returns external pages with schema or field information, ignore those results.

## Three-Phase Execution

Work in three strict phases. **Do not write any output files until Phase 3.**

---

### Phase 1 — Crawl and Inventory

Crawl the site top-down. **Never guess URLs.** Always extract actual links from a page before fetching any subpage.

> **Path note:** The `references/` scripts live at `.claude/skills/croissant/references`
> within the repository root — not in the working directory. The `/robocroissant` command
> instructs you to run `pwd` and construct the absolute path before any other step. Use
> that value as `SKILL_REF` throughout:
> ```bash
> SKILL_REF="$(pwd)/.claude/skills/croissant/references"
> ```
> Then call `python3 $SKILL_REF/fetch.py ...` and `python3 $SKILL_REF/extract.py ...`
> throughout. Never hardcode a username or home directory.

#### Step 1.0 — Discover real URLs from the root

Always begin by fetching the raw HTML of the homepage directly — not through WebFetch, but using `$SKILL_REF/fetch.py`. WebFetch passes the page through an AI model that summarises and filters; it cannot be trusted to return every link. A raw fetch gives you the actual HTML to inspect.

```bash
# Extract all links from the homepage
python3 references/fetch.py --links https://example.org

# Inspect raw HTML structure (look for SPA shells, script tags)
python3 references/fetch.py --raw https://example.org | head -100

# Get both links and readable text at once
python3 references/fetch.py --both https://example.org
```

**Read the raw HTML output, not just the link list.** Look at the structure: Are there custom elements (`<site-nav>`, `<app-root>`)? Script tags loading JS bundles? If the HTML is a thin SPA shell (a few hundred to a few thousand bytes with no real nav links), the navigation is built entirely in JavaScript. In that case:

1. **Extract the JS bundle URL** from the `<script src="...">` tag(s) in the HTML.
2. **Fetch the bundle and extract hrefs and route patterns using `fetch.py --hrefs`:**
   ```bash
   python3 $SKILL_REF/fetch.py --hrefs https://example.org/js/app.js
   ```
   This reliably extracts every internal path the app can navigate to — the full nav menu, footer links, and sub-pages — without needing a browser.

3. **Only if the JS bundle approach fails** (e.g. bundle is too large, obfuscated beyond readability, or loaded dynamically), fall back to: `/sitemap.xml`, `/robots.txt`, a `site:` web search, or asking the user.

**Do not treat WebFetch's inability to see nav links as confirmation that those links don't exist.** A site that returns two links via WebFetch may expose fifty via its JS bundle.

#### Step 1.1 — Follow real links in topical order

Once you have actual URLs from Step 1.0, fetch them in roughly this order, stopping when you have enough:

1. **Homepage** — name, mission, tagline, funder, contact
2. **About / Overview** — org description, history, RRID. Fetch the **full raw text** (never ask for a summary). Follow every link from the about page — journal article links in particular are usually the primary citation.
3. **FAQ / Help** — look for a "How to cite" or "How should I cite" question; this is where databases most commonly declare their primary publication. Also check for license or terms-of-use entries.
4. **License / Terms of use / Data policy** — look for a dedicated page. If none, the verbatim policy text from the about page or FAQ is the source. Do **not** assume CC0 without explicit confirmation.
5. **Publications / Cite us** — some sites have a dedicated page listing publications; fetch it if it exists.
6. **Download / Data** — file names, formats, storage URLs, update frequency, archive paths, access restrictions
7. **Data dictionary / Schema** — column names, types, descriptions, controlled vocabularies. Look for links labelled "Data Dictionary", "Column Descriptions", "Schema", "README", "Documentation", or "Field Definitions". Fetch any linked TSV/CSV/HTML/PDF data dictionaries directly.
8. **API / REST docs** — base URL, endpoints, fields, rate limits, response codes
9. **Sites / Cohorts / Sources** — contributing studies or sub-datasets
10. **Live API endpoint** (e.g. `/info`) — authoritative field lists, record counts, last-modified date

**Citation hunting rules** — `citeAs` expects a journal article, not an RRID or URL. Databases vary widely in where they put this:
- FAQ ("How should I cite?") is the most reliable location
- About page (look for a publications section in the full raw text)
- A dedicated "Publications" or "Cite us" navigation item
- When a site lists multiple papers, look for explicit language like "primary citation", "please cite", or "if you use this resource"
- An RRID (`RRID:SCR_XXXXXX`) is **not** a citation — it is an identifier; put it in `identifier`, not `citeAs`

**Fetching page text** — for metadata-rich pages (about, FAQ, license, publications), use `fetch.py --text` to get clean, complete body text without AI filtering or paraphrasing:

```bash
python3 references/fetch.py --text https://example.org/about
python3 references/fetch.py --text https://example.org/faq
```

Only fall back to WebFetch when `fetch.py` fails (e.g. server blocks non-browser TLS, requires JS execution, or returns a CAPTCHA). If using WebFetch, always request the **complete raw text** — never a summary: *"Return the complete raw text of this page. Do not summarize. Every word, every sentence."*

Fetch pages **in parallel** when they are independent. Follow redirects.

At the end of Phase 1, produce an **inventory table** — one row per downloadable file:

| id | url | format | schema_source |
|----|-----|--------|---------------|
| `all_tsv_zip` | `https://…/All_tsv.zip` | TSV-in-ZIP | `needs_extraction` |
| `targets_fasta` | `https://…/targets.fasta` | FASTA | `well_defined_format` |
| `readme_txt` | `https://…/README.txt` | plain text | `data_dictionary_page` |

Valid `schema_source` values:

- **`data_dictionary_page`** — a crawled page or linked document fully describes the columns; no download needed
- **`well_defined_format`** — format has a fixed, universally-known schema (e.g. FASTA, VCF); no RecordSet needed, FileObject only
- **`needs_extraction`** — column names are not documented; must extract from the file header
- **`blocked`** — download is blocked by authentication or CAPTCHA; cannot extract without credentials

**A file marked `needs_extraction` must never survive to Phase 3.** Every `needs_extraction` item must be resolved in Phase 2 or reclassified as `blocked` if the download itself is gated.

If a data dictionary page exists but does not list all fields, record it as `data_dictionary_page` (partial) and also queue a `needs_extraction` extraction to fill the gaps.

---

### Phase 2 — Resolve `needs_extraction`

For every file still marked `needs_extraction` in the inventory, run the appropriate extraction command below. Run independent extractions **in parallel**.

On success → mark `schema_source: extracted_header`.
On auth/CAPTCHA block → mark `schema_source: blocked`.

**`blocked` means authentication or CAPTCHA only. File size is never a reason to mark a file `blocked`.** For large files, always use a range/partial download to extract the header or schema before giving up.

Use `references/extract.py` for all format extractions. It handles partial/range downloads internally — never fetches the whole file. Exit code 1 means blocked (401/403/CAPTCHA); mark as `blocked` in the inventory.

```bash
# TSV/CSV — direct URL, prints header row
python3 references/extract.py tsv <url>

# TSV/CSV inside a ZIP (including large files)
python3 references/extract.py tsv-zip <url>

# SDF (Structure-Data File) — direct URL, prints property names from first record
python3 references/extract.py sdf <url>

# SDF inside a ZIP (including large files)
python3 references/extract.py sdf-zip <url>

# MySQL dump inside a ZIP — prints CREATE TABLE statements
python3 references/extract.py mysql-zip <url>

# TAR archive — lists first ~200 member filenames and sizes
python3 references/extract.py tar <url>

# JSON file or API response — prints top-level keys
python3 references/extract.py json <url>
```

#### FASTA
No extraction needed. FASTA is a well-defined two-field format (sequence identifier line starting with `>`, followed by the sequence). Document as a FileObject only — no RecordSet. See `references/croissant-schema.md` for the correct `@type` IRI.

---

### Phase 3 — Write Outputs

Only after every inventory item is resolved (status `data_dictionary_page`, `well_defined_format`, `extracted_header`, or `blocked`) write the output files.

Files with status `blocked` go to `{name}_incomplete.json`. That is the **only** valid reason for an incomplete schema entry.

---

### Phase 4 — Validate

After writing `{name}_croissant.json`, run the official validator:

```bash
.venv/bin/mlcroissant validate --jsonld datasets/{name}/{dataset_version}/{local_version}/{name}_croissant.json
```

**Requirement**: `mlcroissant` must be installed in `.venv` in the working directory. If `.venv/bin/mlcroissant` does not exist, stop and tell the user to run:
```bash
uv venv .venv && uv pip install --python .venv/bin/python mlcroissant
```

**On errors**: Fix every `E` (error) line before delivering the output. Do not suppress or work around validator errors — they indicate genuine non-conformance. Re-run the validator after each fix cycle until it reports zero errors.

**On warnings**: Warnings (`W`) about missing recommended fields (`datePublished`, `version`, etc.) should be addressed if the information is available from crawled sources. If not, note them in `{name}_incomplete.json`.

**Content validation** — after the structural validator passes, re-fetch the source page for each of these fields and compare the Croissant value character-by-character against the live page text:

- `citeAs` — re-fetch the citations/FAQ/about page and confirm the full author list, exact title, journal, volume, pages, and year match what is on the page
- `license` — re-fetch the license/terms page and confirm the license URL or verbatim policy text matches
- `name` and `description` — re-fetch the homepage and confirm these are exact quotes, not paraphrases
- `conditionsOfAccess` — re-fetch the terms page and confirm any quoted policy language is verbatim

For each field, fetch the source URL, find the relevant sentence or paragraph, and ask: "Does the Croissant value match the source text exactly, or has it been paraphrased, reformatted, or partially rewritten?" If there is any divergence, correct the Croissant value to match the source exactly.

---

## Incomplete Components File

Use `{name}_incomplete.json` to record Croissant components that could not be completed. The **only** valid reason for an incomplete schema is `blocked` status from Phase 2 (authentication or CAPTCHA). Everything else must be resolved before Phase 3.

Format:

```json
{
  "description": "Croissant components for {name} that could not be completed from crawled pages alone.",
  "generated": "YYYY-MM-DD",
  "items": [
    {
      "component_type": "https://schema.org/FileObject | http://mlcommons.org/croissant/FileSet | http://mlcommons.org/croissant/RecordSet | http://mlcommons.org/croissant/Field",
      "id": "the @id that would be used in the Croissant file",
      "reason": "What is missing and why it could not be sourced",
      "how_to_complete": "Specific action needed — e.g. the login URL to authenticate before downloading"
    }
  ]
}
```

## Provenance Discipline

For every fact written into the Croissant file:
- Assign a `src_*` ID to each crawled URL
- Record the most specific URL possible, including `#anchor` fragments when available
- Distinguish **direct quotes** (use quotation marks in notes) from **inferences**
- Each field in a RecordSet requires its own claim entry, not a blanket note

See `references/provenance-format.md` for the exact provenance file schema.

## Croissant File Structure

See `references/croissant-schema.md` for the full schema.

Top-level fields to always populate if found:
- `conformsTo`: always `"http://mlcommons.org/croissant/1.1"` — **mandatory**
- `name`, `description`, `url`, `identifier` (RRID or DOI)
- `license`, `conditionsOfAccess`, `isAccessibleForFree`
- `creator` (with `parentOrganization` and `funder`)
- `datePublished`, `dateModified`, `temporalCoverage`, `inLanguage`
- `version` (recommended by validator) — use the dataset's own version string if one is published; if not, use the `dateModified` value (YYYY-MM-DD) as the version; only omit if no update date can be found
- `citation` — **must be a plain text string**; do not use a structured `ScholarlyArticle` object
- `keywords`
- `relatedLink`: set to `"{name}_apis.json"` when APIs are documented

Distribution entries (FileObject / FileSet) for every downloadable artifact. **See `references/croissant-schema.md` for required `@type` full IRIs and all naming rules.** Key rules:
- `contentUrl` (exact URL), `encodingFormat` (MIME type), `version` (if versioned)
- **`md5` or `sha256` is required on every FileObject.** Fetch from `.md5` checksum files when available; otherwise compute via streaming download. FileSets do not require checksums.
- **`@type` must be the correct full IRI** — see `references/croissant-schema.md` for the exact IRIs for FileObject, FileSet, RecordSet, and Field. Never use prefixed forms (`cr:FileObject` etc.) — they cause type validation errors.
- **`@id` must be namespaced** — use `"datasetslug/node_id"` (no spaces). Bare slugs cause UUID cross-reference failures in FileSets.
- **`name` must not contain spaces** — use underscores or hyphens.
- For access-restricted data, set `contentUrl` to the request/landing page and use `conditionsOfAccess` (schema.org/CreativeWork) to describe the restriction — do **not** use `cr:accessRestrictions`, which is not a defined Croissant property

RecordSets (full IRI: `http://mlcommons.org/croissant/RecordSet`) with Fields (`http://mlcommons.org/croissant/Field`) for every distinct table or schema:
- Include a RecordSet for every file whose schema_source is `data_dictionary_page` or `extracted_header` after Phase 2
- Omit the RecordSet and add to `{name}_incomplete.json` only for files with schema_source `blocked`
- Use `source.fileObject/@id` to link fields to their distribution
- `dataType`: prefer `sc:Text`, `sc:Integer`, `sc:Number`, `sc:Date`, `sc:Boolean`
- Multi-value fields (pipe-delimited lists) → `sc:Text` with a note in `description`
- Inline small lookup tables using `cr:data`

APIs and Tools — **not part of the Croissant spec**. Document in `{name}_apis.json` (plain JSON) with this structure:

```json
{
  "description": "API and tool documentation for {Dataset Name}. Not part of the Croissant file.",
  "generated": "YYYY-MM-DD",
  "source_url": "https://...",
  "rest_apis": [
    {
      "id": "my_endpoint",
      "name": "endpointName",
      "description": "...",
      "url": "https://...",
      "method": "GET",
      "parameters": [
        {"name": "param1", "description": "...", "type": "string"}
      ],
      "response_formats": ["xml", "json"]
    }
  ],
  "web_tools": [
    {
      "name": "Custom Downloads Portal",
      "description": "...",
      "url": "https://..."
    }
  ]
}
```

## Access Restrictions

If the dataset requires registration or a formal request:
- Set `"isAccessibleForFree": false`
- Describe the process in `conditionsOfAccess` at the dataset level
- Still document the data dictionary / schema if that is publicly available
- For individual files with restrictions, set `conditionsOfAccess` on the FileObject directly — this is a valid schema.org/CreativeWork property

## Common Pitfalls

- **Never write inline Python scripts.** Do not use heredocs (`<<'PYEOF'`) or `python3 -c "..."` multi-line strings for fetching or extraction. Every fetch must go through `fetch.py`; every schema extraction must go through `extract.py`. Inline scripts require user button-presses and bypass the auditable tool chain. If you think you need an inline script, add a mode to `fetch.py` or `extract.py` instead.

- **Guessing URLs**: never guess paths like `/bind/info.jsp` or `/downloads.jsp`. Always extract real links from a fetched page first. Multiple failed guesses in a row means you are doing it wrong — stop and use the sitemap/search/user strategies in Phase 1.0 instead.
- **JavaScript-rendered homepages**: many modern sites are SPAs whose navigation is built entirely in JavaScript. WebFetch will return only the thin HTML shell — a few links at best. Do not treat this as the complete link list. Always fetch the raw HTML via a `requests` script first; if you see custom elements (`<app-nav>`, `<site-header>`) or a tiny page body (under ~5 KB), fetch the referenced JS bundle(s) and grep them for `href` patterns. This will expose the full navigation in seconds. Jumping to sitemap guessing or asking the user without first checking the JS bundle is skipping the obvious step.
- **Parallel failures cascade**: when one request in a parallel batch 404s, the tool cancels the others. Prefer to confirm the URL structure works before batching many speculative fetches in parallel.
- **Training knowledge**: never use it — if you cannot cite a crawled URL, omit the value and add an incomplete item
- **Paraphrasing string fields**: for `citeAs`, `license`, `name`, `description`, and `conditionsOfAccess`, copy the exact text from the source page — do not reformat, abbreviate, or reword. "et al." is not acceptable when the page lists all authors. A paraphrased title is a wrong title. Treat these fields like quoted strings, not summaries.
- **Field counts**: count stored fields from a live API endpoint, not from documentation pages — they often diverge
- **File URLs**: when fetching a download page, explicitly ask for the exact `href` attribute value of every anchor tag — do not ask what files are "available" or for a "description" of downloads, as the WebFetch model will return prose summaries instead of URLs. Correct prompt phrasing: *"List the exact href value of every download link on this page."*
- **License**: if no formal license is stated, do not assume CC0 — describe the policy verbatim in `conditionsOfAccess` and flag the license as inferred in provenance
- **Founding years for cohorts**: use enrollment start year if "established" is ambiguous; note the interpretation
- **CAPTCHA-blocked pages**: skip gracefully; add an incomplete item with the blocked URL and what it would have provided
- **Large files**: never mark a file `blocked` just because it is large. Always attempt a partial download first using the range-request or `--max-filesize` recipes in Phase 2. A 500 MB ZIP's header is in the first few KB; a MySQL dump's CREATE TABLE statements are near the top; a TAR's file list is in the first 512-byte blocks. Only mark `blocked` if the server returns 401/403 or presents a CAPTCHA.
- **Quoted strings in chained Bash commands trigger permission prompts**: the permission matcher checks the full command string, so embedding shell-quoted strings (e.g. `echo "---"`) inside a `&&` chain causes the entire command to fail permission matching even when `Bash(python3 *)` is in the allow list. Never use quoted strings as separators or labels inside chained commands. Use separate Bash tool calls, or unquoted separators like `echo ---`, instead.
- **Servlet/session-gated downloads**: some sites serve files through a server-side servlet (e.g. Java `.jsp`, `.do`, PHP scripts) that checks for a valid browser session cookie before delivering the file. Symptoms: `curl` returns HTML instead of the expected binary, or the response body is empty. In this case, `curl` alone will not work. Instead, write a short Python `requests` script that (1) `GET`s the download page to obtain a session cookie, (2) re-uses that cookie (and sets an appropriate `Referer` header) to `GET` the file URL with `stream=True`, and (3) reads only the first chunk needed (e.g. 5 MB) to extract the header — never downloading the whole file. This is the correct workaround for publicly available files that happen to be gated behind a session; do not mark such files `blocked`.

## Iteration

Corrections and additions always produce a **new local version** — increment `{local_version}` and write fresh copies of all four files into the new directory. Do not edit files in a previous run directory.

**Prior run directories are off-limits** unless the user explicitly grants access (e.g. "you can look at run 2"). If the user refers to a prior run without granting access, ask them to share the relevant content rather than reading it yourself.

If the user provides corrections or additional facts:
1. Determine the new `{local_version}` by scanning existing directories
2. Create `datasets/{name}/{dataset_version}/{local_version}/`
3. Copy forward the prior files (ask the user to paste them, or request read access to the prior run if they grant it), apply the corrections, and write all four files into the new directory

If the user downloads a file and provides column headers or schema information:
1. Add the RecordSet / Fields to the Croissant file
2. Add provenance claims attributed to `src_user_provided` with a note describing what was shared
3. Remove the corresponding incomplete item
