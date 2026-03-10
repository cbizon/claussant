---
description: Generate a verified Croissant metadata file for a dataset from its URL.
argument-hint: <DATASET_URL>
---

Generate a Croissant metadata file for the dataset at $ARGUMENTS.

The skill reference scripts live at `.claude/skills/croissant/references` within this
repository. Before running any reference scripts, determine the absolute path by running:

```bash
pwd
```

Set SKILL_REF to `{result}/.claude/skills/croissant/references` and use that variable
for all calls to `fetch.py`, `extract.py`, `nextver.py`, and `check_provenance.py`.

IMPORTANT: Follow the croissant skill exactly for all phases of execution.
