#!/usr/bin/env python3
"""
Print the next local_version integer for a given versioned output directory.

Usage:
  python3 references/nextver.py {name}/{dataset_version}

Scans the directory for subdirectories whose names are plain integers,
takes the highest, and prints highest+1. Prints 1 if the directory does
not exist or contains no integer subdirectories.
"""

import os
import re
import sys

if len(sys.argv) != 2:
    print(__doc__)
    sys.exit(2)

d = sys.argv[1]
existing = [int(x) for x in os.listdir(d) if re.fullmatch(r"[0-9]+", x)] if os.path.isdir(d) else []
print(max(existing) + 1 if existing else 1)
