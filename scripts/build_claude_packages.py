#!/usr/bin/env python3
"""Build every task-specific package for normal Claude into ./claude_packages/
using the knowledge in your real store (config db_path, default data/marketing.db).

    python3 scripts/build_claude_packages.py [--product NAME] [--audience TEXT] [--db PATH]
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from marketing_toolkit import export  # noqa: E402
from marketing_toolkit.config import load_config  # noqa: E402
from marketing_toolkit.store import KnowledgeStore  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product")
    ap.add_argument("--audience")
    ap.add_argument("--db")
    ap.add_argument("--out", default=str(ROOT / "claude_packages"))
    a = ap.parse_args()
    store = KnowledgeStore(a.db or load_config()["db_path"])
    for task in export.TASKS:
        r = export.build_package(task, store, a.out, a.product, a.audience)
        m = r["manifest"]
        print(f"{task:28s} {len(m['files']):3d} files {m['total_bytes'] / 1024:7.1f} KB  knowledge={m['knowledge_records']:<4d} -> {r['zip']}")
    store.close()


if __name__ == "__main__":
    main()
