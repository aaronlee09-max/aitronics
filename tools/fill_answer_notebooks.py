#!/usr/bin/env python3
"""Copy each student .ipynb and fill blanks only. Keep original format."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MD_REPL = [
    ('→ ( ) 개', '→ **344개**'),
    ('→ ( ) 명', '→ **200명**'),
    ('→ ( ) 년', '→ **2016년**'),
    ('→ ( )%', '→ **30%**'),
    ('테스트 데이터는 전체의 몇 %인가?  → ( )', '테스트 데이터는 전체의 몇 %인가?  → **30%**'),
    ('→ ( ) ~ ( )', '→ **0 ~ 1**'),
    ('결측치가 있는 속성이 있는가?  → ( )', '결측치가 있는 속성이 있는가?  → **없다**'),
    ('타깃이 필요한가?  → ( )', '타깃이 필요한가?  → **필요 없다**'),
    ('순위를 뜻하는가?  → ( )', '순위를 뜻하는가?  → **아니다**'),
    ('더 좋은 군집이라는 뜻인가?  → ( )', '더 좋은 군집이라는 뜻인가?  → **아니다. 번호는 이름표일 뿐이다.**'),
    ('오른쪽 위 / 오른쪽 아래 / 왼쪽 위 / 왼쪽 아래)  → ( )', '오른쪽 위 / 오른쪽 아래 / 왼쪽 위 / 왼쪽 아래)  → **오른쪽 위**'),
    ('k=5일 때 실루엣 점수는 약 얼마인가?  → ( )', 'k=5일 때 실루엣 점수는 약 얼마인가?  → **약 0.55**'),
    ('가장 높은 k는 얼마인가?  → ( )', '가장 높은 k는 얼마인가?  → **보통 5**'),
    ('분류인가?  → ( )', '분류인가?  → **분류**'),
    ('타깃은 무엇인가?  → ( )', '타깃은 무엇인가?  → **species(펭귄 종)**'),
    ('정확도는 약 얼마인가?  → ( )', '정확도는 약 얼마인가?  → **훈련 약 1.00 / 테스트 약 0.94**'),
    ('훈련 ( ) 개 · 테스트 ( ) 개', '훈련 **약 233개** · 테스트 **약 101개**'),
    ('메서드는 무엇인가?  → ( )', '메서드는 무엇인가?  → **predict() / score()**'),
]

CODE_HINTS = [
    ('판다스 라이브러리 가져오기', "import pandas as pd\ndf = pd.read_csv('penguins_size.csv')\ndf.head()\n"),
    ('데이터 속성 확인하기', 'df.info()\n'),
    ('데이터 통계 정보 요약', 'df.describe()\n'),
    ('countplot', "import seaborn as sns\nimport matplotlib.pyplot as plt\nsns.countplot(data=df, x='species')\nplt.show()\n"),
    ('결측치 개수 확인하기', "print(df.isnull().sum())\ndf.dropna(axis=0, inplace=True)\ndf.info()\n"),
    ('데이터 프레임 요약 정보', "import pandas as pd\ndf = pd.read_csv('penguins_size.csv')\ndf.info()\n"),
    ('pandas 불러오기', "import pandas as pd\ndf = pd.read_csv('Mall_Customers.csv')\nprint(df.head())\nprint(df.info())\nprint(df.isnull().sum())\n"),
    ('KMeans', "from sklearn.cluster import KMeans\nmodel = KMeans(n_clusters=5, random_state=42, n_init=10)\nmodel.fit(data)\n"),
    ('DecisionTreeClassifier', "from sklearn.tree import DecisionTreeClassifier\ndt = DecisionTreeClassifier(random_state=42)\ndt.fit(X_train, y_train)\nprint(dt.score(X_train, y_train))\n"),
    ('plot_tree', "from sklearn.tree import plot_tree\nimport matplotlib.pyplot as plt\nplt.figure(figsize=(20,10))\nplot_tree(dt, max_depth=2, filled=True)\nplt.show()\n"),
    ('silhouette', "from sklearn.metrics import silhouette_score\nprint(silhouette_score(data, model.labels_))\n"),
    ('MinMaxScaler', "from sklearn.preprocessing import MinMaxScaler\nscaler = MinMaxScaler()\ndata = scaler.fit_transform(data)\nprint(data[:5])\n"),
    ('train_test_split', "from sklearn.model_selection import train_test_split\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)\nprint(X_train.shape, X_test.shape)\n"),
]


def to_src(text: str) -> list[str]:
    if not text.endswith('\n'):
        text += '\n'
    return text.splitlines(keepends=True)


def is_blank_code(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return (not lines) or all(ln.startswith('#') for ln in lines)


def fill_md(text: str) -> str:
    out = text
    for a, b in MD_REPL:
        if a in out:
            out = out.replace(a, b)
    # leftover empty arrows in 확인하기 / 마무리
    out = out.replace('→ ( )', '→ **(교과서·실행 결과 참고)**')
    return out


def fill_code(text: str) -> str:
    if 'subprocess' in text:
        return text
    if 'def ensure_csv(' in text:
        return text
    if not is_blank_code(text):
        return text
    for hint, body in CODE_HINTS:
        if hint in text:
            return text.rstrip() + '\n' + body
    return text


def main() -> None:
    students = []
    for p in ROOT.rglob('*.ipynb'):
        if '_정답' in p.name or 'jlite' in p.parts:
            continue
        if not any(part.startswith('ch2-') or part.startswith('ch3-') for part in p.parts):
            continue
        if p.parent.name in {'ch2-1', '2', '3', '4', 'ch2-3', 'ch3-3', 'ch3-4'}:
            students.append(p)
    for student in sorted(students):
        nb = json.loads(student.read_text(encoding='utf-8'))
        for cell in nb.get('cells', []):
            src = ''.join(cell.get('source', []))
            if cell.get('cell_type') == 'markdown':
                cell['source'] = to_src(fill_md(src))
            elif cell.get('cell_type') == 'code':
                new = fill_code(src)
                if new != src:
                    cell['source'] = to_src(new)
                    cell['outputs'] = []
                    cell['execution_count'] = None
        out = student.with_name(student.stem + '_정답.ipynb')
        out.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print('wrote', out.relative_to(ROOT))


if __name__ == '__main__':
    main()
