# Croissant JSON-LD Schema Reference

Croissant is a metadata format for machine-learning datasets published by MLCommons.
Specification: https://docs.mlcommons.org/croissant/docs/croissant-spec-1.1.html

**Namespace discipline**: Only use properties that are actually defined in the referenced namespaces. Do not invent properties under `cr:`, `sc:`, or any other namespace — that pollutes vocabularies you don't own. If there is no schema.org or Croissant property for something, either find the right vocabulary or leave it out of the Croissant file.

## Context Block

Use the **full canonical context** exactly as shown below. Note `@vocab` and `sc` must be `https://schema.org/` (**HTTPS**) — the spec appendix says `http://` but the mlcroissant validator (confirmed on v1.0.22) uses HTTPS internally for its valid-dataType list and distribution-property lookups. Using HTTP causes "invalid dataType" and "node doesn't exist" validation errors.

```json
{
  "@context": {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "sc": "https://schema.org/",
    "cr": "http://mlcommons.org/croissant/",
    "rai": "http://mlcommons.org/croissant/RAI/",
    "dct": "http://purl.org/dc/terms/",
    "annotation": "cr:annotation",
    "arrayShape": "cr:arrayShape",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "containedIn": "cr:containedIn",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "equivalentProperty": "cr:equivalentProperty",
    "examples": {"@id": "cr:examples", "@type": "@json"},
    "excludes": "cr:excludes",
    "extract": "cr:extract",
    "field": "cr:field",
    "fileProperty": "cr:fileProperty",
    "fileObject": "cr:fileObject",
    "fileSet": "cr:fileSet",
    "format": "cr:format",
    "includes": "cr:includes",
    "isArray": "cr:isArray",
    "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath",
    "key": "cr:key",
    "md5": "cr:md5",
    "parentField": "cr:parentField",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "readLines": "cr:readLines",
    "sdVersion": "cr:sdVersion",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
    "unArchive": "cr:unArchive",
    "value": "cr:value"
  }
}
```

**Divergences between spec and validator `make_context()`**: The installed `mlcroissant` validator's `make_context()` differs from the spec in a few ways — it adds `samplingRate`, `path`, `repeated`, `replace`, and omits several spec keys (`annotation`, `excludes`, `readLines`, `sdVersion`, `unArchive`, `value`). The warning about missing keys is cosmetic. However, the validator uses `https://schema.org/` (HTTPS) for `@vocab` and `sc` — this is **not** cosmetic: using HTTP causes real validation errors (invalid dataType, node cross-reference failures). Always use HTTPS for `@vocab` and `sc` regardless of what the spec appendix says.

## CRITICAL: `@type` values must be full IRIs — never prefixed forms

**This is the single most common cause of validator errors.** The `mlcroissant` validator compares `@type` as a raw Python string against the full expanded IRI. Prefixed forms like `cr:FileObject` or `sc:FileObject` are **never equal** to the full IRI string even when the context maps them correctly.

Use these exact literal strings — no shortcuts:

| Object | Required `@type` value |
|--------|----------------------|
| Dataset (top level) | `"https://schema.org/Dataset"` |
| FileObject | `"http://mlcommons.org/croissant/FileObject"` |
| FileSet | `"http://mlcommons.org/croissant/FileSet"` |
| RecordSet | `"http://mlcommons.org/croissant/RecordSet"` |
| Field | `"http://mlcommons.org/croissant/Field"` |
| Organization | `"https://schema.org/Organization"` |
| Person | `"https://schema.org/Person"` |

All Croissant node types (`FileObject`, `FileSet`, `RecordSet`, `Field`) live in the `http://mlcommons.org/croissant/` namespace in Croissant v1.0/v1.1. In the older v0 spec, `FileObject` was `https://schema.org/FileObject` — the validator source (`constants.py`) confirms this migration: `SCHEMA_ORG.FileObject if ctx.is_v0() else ML_COMMONS(ctx)["FileObject"]`.

Why `sc:Dataset` works at the top level but nothing else does: the top-level `@type` is processed by a different code path that does JSON-LD expansion first. For nested objects inside `distribution` and `recordSet`, the validator extracts the raw string with `value.get("@type")` and compares it directly — no expansion. Always use full IRIs for ALL `@type` values to be safe.

## Dataset (top level)

`conformsTo` is **mandatory** per the Croissant 1.1 spec. Every output file must include it. `datePublished` and `version` are recommended by the validator.

```json
{
  "@type": "https://schema.org/Dataset",
  "@id": "my_dataset",
  "conformsTo": "http://mlcommons.org/croissant/1.1",
  "name": "...",
  "description": "...",
  "url": "https://...",
  "identifier": "RRID:SCR_XXXXXX",
  "version": "current",
  "license": "https://creativecommons.org/publicdomain/zero/1.0/",
  "conditionsOfAccess": "...",
  "isAccessibleForFree": true,
  "keywords": ["..."],
  "inLanguage": "en",
  "datePublished": "YYYY-MM-DD",
  "dateModified": "YYYY-MM-DD",
  "temporalCoverage": "YYYY/..",
  "citation": "Full citation as a plain text string.",
  "creator": { "@type": "Organization", "name": "...", "url": "..." },
  "publisher": { "@type": "Organization", "name": "...", "url": "..." },
  "funder": { "@type": "Organization", "name": "...", "url": "..." },
  "maintainer": { "@type": "Person", "email": "...", "name": "..." },
  "spatialCoverage": { "@type": "Place", "name": "..." },
  "hasPart": [],
  "distribution": [],
  "recordSet": [],
  "relatedLink": "{name}_apis.json"
}
```

Notes:
- `citation` must be a **plain text string** — do not use `{"@type": "ScholarlyArticle", ...}`. The validator rejects structured citation objects.
- `recordSet` (shorthand from context) is the correct key for the RecordSet array; `cr:recordSet` also works but `recordSet` is cleaner with the canonical context.
- `relatedLink` (schema.org/CreativeWork) points to the companion APIs file when one exists. Omit if there are no APIs to document.

## FileObject

A single downloadable file.

```json
{
  "@type": "http://mlcommons.org/croissant/FileObject",
  "@id": "mydataset/my_file_tsv",
  "name": "my_file_tsv",
  "description": "...",
  "contentUrl": "https://...",
  "encodingFormat": "text/tab-separated-values",
  "version": "2025-10-07",
  "md5": "d41d8cd98f00b204e9800998ecf8427e",
  "conditionsOfAccess": "Requires data access request via ..."
}
```

**`md5` or `sha256` is required** on every FileObject — the validator enforces this. Always fetch or compute the actual checksum. If the dataset provides `.md5` checksum files alongside downloads, fetch those and use the hash string directly (not the URL to the file). If neither is available (e.g., for very large files or access-restricted files), compute a streaming MD5 from a partial download and note it as partial in provenance.

**`@id` must be namespaced**: Use a dataset-slug prefix (e.g. `"mydataset/my_file_tsv"`) to avoid UUID collisions and expansion issues. Plain strings like `"my_file_tsv"` may cause cross-reference failures when the validator resolves UUIDs.

**`name` must not contain spaces** — use underscores or hyphens. Names with spaces cause "forbidden characters" validator errors on FileSets and their cross-references.

`conditionsOfAccess` is the schema.org/CreativeWork property for access restrictions — use it on individual FileObjects when they have restrictions different from the dataset as a whole. Do **not** use `cr:accessRestrictions`; that property is not defined in the Croissant spec.

Common MIME types:
- `text/tab-separated-values` — TSV
- `text/csv` — CSV
- `application/json` — JSON
- `application/rdf+xml` — OWL / RDF/XML
- `application/ld+json` — JSON-LD
- `application/parquet` — Parquet
- `application/zip` — ZIP archive

## FileSet

A collection of files matching a pattern.

```json
{
  "@type": "http://mlcommons.org/croissant/FileSet",
  "@id": "mydataset/monthly_archives",
  "name": "monthly_archives",
  "description": "...",
  "containedIn": [{"@id": "mydataset/archive_zip"}],
  "encodingFormat": "text/tab-separated-values",
  "includes": "*.txt"
}
```

**`name` must not contain spaces** — use underscores or hyphens.

**`@id` must be namespaced** — same rule as FileObject.

**`containedIn`** references the parent FileObject(s) by `@id`. The `@id` values in `containedIn` must exactly match the `@id` values on the FileObject entries — the validator checks this with a UUID string comparison. A mismatch causes "this node doesn't exist" errors.

**`includes`** is required on a FileSet. The context shorthand `includes` maps to `cr:includes` (`http://mlcommons.org/croissant/includes`), which is what the validator expects when the document version is correctly detected as v1.0/v1.1.

FileSets do **not** require `md5`/`sha256` — that is only required on FileObjects.

## RecordSet

A logical table or schema. Contains an array of `field` entries.

```json
{
  "@type": "http://mlcommons.org/croissant/RecordSet",
  "@id": "mydataset/my_table",
  "name": "my_table",
  "description": "...",
  "field": [],
  "data": []
}
```

Use `data` to inline small reference/lookup tables directly as an array of objects.

## Field

One column or variable within a RecordSet.

```json
{
  "@type": "http://mlcommons.org/croissant/Field",
  "@id": "mydataset/my_table/my_column",
  "name": "my_column",
  "description": "...",
  "dataType": "sc:Text",
  "source": {
    "fileObject": { "@id": "mydataset/my_file_tsv" },
    "extract": { "column": "my_column" }
  }
}
```

`dataType` values: `sc:Text`, `sc:Integer`, `sc:Float`, `sc:Date`, `sc:DateTime`, `sc:Boolean`, `sc:URL`

**`sc:Number` is not valid** — the validator's `DataType` class does not include it. Use `sc:Float` for decimal values. Also valid but less common: `sc:AudioObject`, `sc:ImageObject`, `sc:VideoObject`, `cr:BoundingBox`, `cr:Split`, and the precision-typed variants `cr:Float16`, `cr:Float32`, `cr:Float64`, `cr:Int8` … `cr:Int64`, `cr:UInt8` … `cr:UInt64`.

For Fields sourcing from a FileSet (rather than a specific FileObject), use `"fileSet": {"@id": "..."}` in the `source` instead of `"fileObject"`.

## APIs and Tools (companion file only)

`cr:Service`, `cr:Tool`, `cr:Endpoint`, `cr:requestMethod`, `cr:requestParameter` are **not defined in the Croissant 1.1 spec**. Do not include them in the Croissant file. Document APIs and tools in the companion `{name}_apis.json` file instead — see the SKILL.md for the format.

## Organization (reusable sub-object)

```json
{
  "@type": "https://schema.org/Organization",
  "name": "...",
  "url": "https://...",
  "parentOrganization": { "@type": "https://schema.org/Organization", "name": "...", "url": "..." },
  "funder": { "@type": "https://schema.org/Organization", "name": "...", "url": "..." }
}
```

## Common Validator Pitfalls (confirmed by testing against mlcroissant)

1. **Prefixed `@type` always fails for nested objects.** `cr:FileObject`, `sc:FileObject`, `cr:RecordSet` etc. will produce type errors on every node. Use the full IRI literals from the table above.

2. **`md5` or `sha256` is required on every FileObject.** A FileObject with no checksum field produces an error. Always fetch the real hash from the dataset's checksum files. If not provided, compute via streaming download.

3. **`name` must not contain spaces.** FileSet (and other node) names with spaces trigger "forbidden characters" errors. Use underscores or hyphens.

4. **`@id` cross-references are string-compared exactly.** The `@id` you put on a FileObject must be character-for-character identical to the `@id` you reference in `containedIn` on a FileSet and in `fileObject`/`fileSet` source references in Fields. Use a namespaced slug pattern (`"datasetname/node_name"`) throughout to avoid UUID expansion issues.

5. **`datePublished` and `version` are recommended, not required.** The validator emits warnings (W) for these but not errors (E). Include them if sourced from a crawled page; otherwise accept the warning.

6. **`citation` must be a plain string.** Do not use `{"@type": "ScholarlyArticle", ...}`. The validator rejects structured citation objects.

7. **FileSets do not need `md5`/`sha256`.** The checksum requirement applies only to FileObjects.

8. **`sc:Number` is rejected as a `dataType`.** Use `sc:Float` for decimals. The validator's `DataType` class omits `sc:Number` entirely despite it being a valid schema.org class. Confirmed in `mlcroissant/_src/core/constants.py`.

9. **FileObject `@type` changed between v0 and v1.** In Croissant v0, FileObject was `https://schema.org/FileObject`. In v1.0/v1.1 it moved to `http://mlcommons.org/croissant/FileObject`. The validator switches based on `ctx.is_v0()`. Always use the v1 IRI.
