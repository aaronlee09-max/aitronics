#!/usr/bin/env python3
"""Copy each student .ipynb and fill blanks only. Do not compact into 빠답."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def src_list(text: str) -> list[str]:
    if not text.endswith("\n"):
        text += "\n"
    return text.splitlines(keepends=True)


def main() -> None:
    fills = json.loads((Path(__file__).with_name("answer_fills.json")).read_text(encoding="utf-8"))
    for item in fills:
        student = ROOT / item["student"]
        if not student.exists():
            print("missing", student)
            continue
        nb = json.loads(student.read_text(encoding="utf-8"))
        cells = nb.get("cells", [])
        for i, code in item["code_fills"].items():
            i = int(i)
            if i < len(cells) and cells[i].get("cell_type") == "code":
                cells[i]["source"] = src_list(code)
                cells[i]["outputs"] = []
                cells[i]["execution_count"] = None
        for i, md in item["md_fills"].items():
            i = int(i)
            if i < len(cells) and cells[i].get("cell_type") == "markdown":
                cells[i]["source"] = src_list(md)
        out = student.with_name(student.stem + "_정답.ipynb")
        out.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("wrote", out.relative_to(ROOT), "cells", len(cells))


if __name__ == "__main__":
    main()
