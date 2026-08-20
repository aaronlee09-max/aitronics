#!/usr/bin/env python3
"""Detect practice notebooks that still need a filled 정답 copy."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNER = (
    "# 정답 노트북\n\n"
    "이 파일은 빈칸을 채운 학습용 정답입니다. "
    "먼저 빈칸 노트북으로 직접 풀어 본 뒤 비교하세요.\n"
)


def cell_text(cell: dict) -> str:
    src = cell.get("source", [])
    if isinstance(src, list):
        return "".join(src)
    return str(src)


def is_blank_code(cell: dict) -> bool:
    if cell.get("cell_type") != "code":
        return False
    text = cell_text(cell).strip()
    if not text:
        return True
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return bool(lines) and all(ln.startswith("#") for ln in lines)


def load_nb(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def answer_path(path: Path) -> Path:
    return path.with_name(path.stem + "_정답.ipynb")


def has_banner(nb: dict) -> bool:
    if not nb.get("cells"):
        return False
    first = nb["cells"][0]
    return first.get("cell_type") == "markdown" and "정답 노트북" in cell_text(first)


def copy_complete_as_answer(src: Path) -> None:
    dest = answer_path(src)
    if dest.exists():
        return
    nb = load_nb(src)
    if any(is_blank_code(c) for c in nb.get("cells", [])):
        return
    if not has_banner(nb):
        nb["cells"].insert(0, {"cell_type": "markdown", "metadata": {}, "source": [BANNER]})
    dest.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"CREATED {dest.relative_to(ROOT)}")


def main() -> int:
    practice = [
        p for p in ROOT.rglob("*.ipynb")
        if "_정답" not in p.name and ".ipynb_checkpoints" not in str(p)
    ]
    missing = []
    blanks = []
    for path in sorted(practice):
        rel = path.relative_to(ROOT)
        nb = load_nb(path)
        blank_cells = [i for i, cell in enumerate(nb.get("cells", [])) if is_blank_code(cell)]
        dest = answer_path(path)
        if blank_cells:
            blanks.append((rel, blank_cells))
        if not dest.exists():
            missing.append(rel)
            copy_complete_as_answer(path)

    print("== blank practice notebooks ==")
    if not blanks:
        print("(none)")
    for rel, cells in blanks:
        print(f"{rel}: blank code cells {cells}")

    print("== missing 정답 files ==")
    if not missing:
        print("(none)")
    for rel in missing:
        print(rel)

    still_missing = [
        p.relative_to(ROOT)
        for p in practice
        if not answer_path(p).exists() and any(is_blank_code(c) for c in load_nb(p).get("cells", []))
    ]
    if still_missing:
        print("== needs manual fill ==")
        for rel in still_missing:
            print(rel)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
