# Provenance File Format

Every Croissant file produced by this skill must have a companion `{name}_provenance.json` file.

## Top-Level Structure

```json
{
  "description": "Provenance records for {name}_croissant.json. Each entry maps a Croissant element to the URL(s) from which the information was extracted, including page anchors where applicable.",
  "crawl_date": "YYYY-MM-DD",
  "crawled_urls": [ ... ],
  "claims": [ ... ],
  "unverified_or_inferred": [ ... ]
}
```

## crawled_urls

One entry per URL fetched. Assign a short `id` (e.g. `src_about`, `src_rest_live`) that is referenced by claims.

```json
{
  "id": "src_about",
  "url": "https://www.example.org/about/",
  "anchor": "#data-policy",
  "description": "What was learned from this URL."
}
```

- `anchor`: include `#fragment` when the specific section anchor is known; `null` otherwise
- `description`: one sentence summarising what facts came from this page

## claims

One entry per significant fact in the Croissant file. Use dot-notation or `@id` paths for `croissant_id`.

```json
{
  "croissant_id": "my_dataset/license",
  "value": "https://creativecommons.org/publicdomain/zero/1.0/",
  "sources": ["src_about"],
  "notes": "Direct quote from the data release policy section: 'No restrictions are imposed...'"
}
```

- `sources`: array of `id` values from `crawled_urls`
- `notes`: required when the value is a direct quote (use quotation marks), or when interpretation was needed
- `value`: the actual value written into the Croissant file, or a summary if it is long

## unverified_or_inferred

Items that could not be confirmed from crawled pages. These are not errors — they are honest disclosures.

```json
{
  "croissant_id": "hgnc_complete_set_tsv/contentUrl",
  "note": "Exact filename inferred from path convention described on the download page. Not confirmed by direct file fetch."
}
```

Common reasons to put something here:
- Exact filename inferred from a path pattern
- License inferred from policy language (no formal SPDX identifier stated)
- Column name not listed on any crawled page (inferred from known schema)
- Page blocked by CAPTCHA — value from prior knowledge only
- Founding year not listed; inferred from enrollment start date

## Cross-Check Requirement

After writing both `{name}_croissant.json` and `{name}_provenance.json`, run:

```bash
python3 $SKILL_REF/check_provenance.py datasets/{name}/{dataset_version}/{local_version}/{name}_croissant.json datasets/{name}/{dataset_version}/{local_version}/{name}_provenance.json
```

Fix every mismatch before delivering output. Common causes:
- Using a schema.org property name (`citation`) instead of the Croissant JSON-LD key (`citeAs`)
- Using a human-readable label instead of the `@id` value
- Using the wrong key (`field` instead of `croissant_id`)

## Guidance

- **`croissant_id` must use the exact key as written in the Croissant JSON-LD** — not the schema.org property name, not the human-readable label. If the Croissant file has `"citeAs": "..."`, the provenance entry must use `croissant_id: "citeAs"` or `"datasetslug/citeAs"`, never `"citation"`.
- Be specific: "Direct quote: '...'" is better than "from the about page"
- Use `#anchor` fragments for sections within pages whenever you know the anchor name
- If a live API endpoint provides an authoritative value (e.g. field count, record count, lastModified), prefer it over documentation pages and note the discrepancy if they differ
- When the same fact appears on multiple pages, list all confirming sources
- Do not omit claims just because they seem obvious — the provenance file should be complete enough to reconstruct the Croissant from scratch
