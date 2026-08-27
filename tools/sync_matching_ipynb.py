#!/usr/bin/env python3
import json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DIR_CSVS = {
    'ai/ch2-1': [('earthquake.csv', 'ai/ch2-1/earthquake.csv'), ('penguins_size.csv', 'ai/ch2-1/penguins_size.csv')],
    'ai/ch2-2/2': [('jeans.csv', 'ai/ch2-2/2/jeans.csv'), ('abalone_original.csv', 'ai/ch2-2/2/abalone_original.csv')],
    'ai/ch2-2/3': [('penguins_size.csv', 'ai/ch2-2/3/penguins_size.csv'), ('food.csv', 'ai/ch2-2/3/food.csv'), ('airline_passenger_satisfaction.csv', 'ai/ch2-2/3/airline_passenger_satisfaction.csv')],
    'ai/ch2-2/4': [('Mall_Customers.csv', 'ai/ch2-2/4/Mall_Customers.csv'), ('caffe_menu.csv', 'ai/ch2-2/4/caffe_menu.csv')],
}

ENSURE = '''# CSV 자동 준비 (Colab · JupyterLite · 로컬 공통)
import sys
from pathlib import Path

def ensure_csv(filename, repo_path):
    candidates = [Path(filename), Path(repo_path), Path("files")/repo_path, Path("/files")/repo_path]
    for c in candidates:
        try:
            if c.is_file():
                if not Path(filename).exists():
                    Path(filename).write_bytes(c.read_bytes())
                return filename
        except Exception:
            pass
    url = f"https://raw.githubusercontent.com/aaronlee09-max/informatics/main/{repo_path}"
    try:
        if sys.platform == "emscripten":
            from pyodide.http import open_url
            Path(filename).write_text(open_url(url).read(), encoding="utf-8")
        else:
            import urllib.request
            urllib.request.urlretrieve(url, filename)
        print("CSV 준비:", filename)
        return filename
    except Exception as e:
        print("CSV 준비 실패 → URL 사용:", url, e)
        return url

'''

def inject_csv(path: Path):
    rel_dir = str(path.parent.relative_to(ROOT)).replace('\\', '/')
    csvs = DIR_CSVS.get(rel_dir)
    if not csvs:
        return
    existing = [(n, r) for n, r in csvs if (ROOT / r).exists()]
    if not existing:
        return
    nb = json.loads(path.read_text(encoding='utf-8'))
    idx = next((i for i, c in enumerate(nb['cells']) if c.get('cell_type') == 'code'), None)
    if idx is None:
        return
    src = ''.join(nb['cells'][idx].get('source', []))
    if 'def ensure_csv(' in src:
        return
    whole = '\n'.join(''.join(c.get('source', [])) for c in nb['cells'])
    used = [(n, r) for n, r in existing if n in whole] or existing
    calls = '\n'.join(f"ensure_csv({n!r}, {r!r})" for n, r in used)
    new = ENSURE + calls + '\n\n' + src
    lines = new.splitlines(keepends=True)
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    nb['cells'][idx]['source'] = lines
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('csv', path.relative_to(ROOT))

def patch_ai_index():
    p = ROOT / 'ai' / 'index.html'
    if not p.exists():
        return
    t = p.read_text(encoding='utf-8')
    if '정답Colab' in t:
        print('ai/index already patched')
        return
    def repl(m):
        href = m.group(1)
        path = href.lstrip('./')
        colab = f'https://colab.research.google.com/github/aaronlee09-max/informatics/blob/main/ai/{path}'
        jlite = f'./jlite/notebooks/index.html?path={path}'
        return (
            f'<a class="download run" href="{colab}" target="_blank" rel="noopener">정답Colab</a>'
            f'<a class="download site" href="{jlite}">정답실행</a>'
            + m.group(0)
        )
    nt = re.sub(r'<a class="download answer" href="(\./[^"]+_정답\.ipynb)" download>정답</a>', repl, t)
    if nt != t:
        p.write_text(nt, encoding='utf-8')
        print('patched ai/index.html')
    else:
        print('no answer buttons matched')

def find_bloom():
    for cand in [Path('bloom'), Path('/tmp/bloom'), ROOT / 'bloom']:
        if cand.exists():
            return cand
    raise SystemExit('bloom checkout missing')

def main():
    bloom = find_bloom()
    n = 0
    for src in bloom.rglob('*.ipynb'):
        rel = src.relative_to(bloom)
        if '_정답' in src.name or any(x in rel.parts for x in ('jlite', 'textbook', '.git')):
            continue
        dst = ROOT / rel
        if dst.exists():
            shutil.copy2(src, dst)
            inject_csv(dst)
            print('OVERWRITE', rel)
            n += 1
        else:
            print('SKIP', rel)
    print('OVERWRITTEN', n)
    patch_ai_index()

if __name__ == '__main__':
    main()
