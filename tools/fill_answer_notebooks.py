#!/usr/bin/env python3
"""Fill *_정답.ipynb from student notebooks using textbook code/answers."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def to_src(text: str) -> list[str]:
    if not text.endswith("\n"):
        text += "\n"
    return text.splitlines(keepends=True)


def join(cell) -> str:
    src = cell.get("source", [])
    return "".join(src) if isinstance(src, list) else str(src)


def set_code(cell, text: str) -> None:
    cell["source"] = to_src(text)
    cell["outputs"] = []
    cell["execution_count"] = None


def set_md(cell, text: str) -> None:
    cell["source"] = to_src(text)


def fill_s3(nb):
    empties = []
    for i, cell in enumerate(nb["cells"]):
        t = join(cell)
        ct = cell.get("cell_type")
        if ct == "code" and "데이터 프레임 요약 정보" in t and "dropna" not in t:
            set_code(cell, "import pandas as pd\ndf = pd.read_csv('penguins_size.csv')\ndf.info()  # 데이터 프레임 요약 정보\n")
        elif ct == "code" and "결측치 개수 확인하기" in t:
            set_code(cell, "df.isnull().sum()     # 결측치 개수 확인하기\n# 행 방향으로 결측치를 제거하고, 데이터 프레임(df) 수정하기\ndf.dropna(axis=0, inplace=True)\ndf.info()    # 데이터 프레임 요약 정보\n")
        elif ct == "code" and "모델 생성하기" in t:
            set_code(cell, "from sklearn.tree import DecisionTreeClassifier\ndt = DecisionTreeClassifier()               # 모델 생성하기\ndt.fit(X_train, y_train)                    # 모델 학습하기\n# 훈련 데이터로 결정트리 모델 분류 정확도 구하기\nprint(dt.score(X_train, y_train))\n")
        elif ct == "code" and "plot_tree" in t:
            set_code(cell, "import matplotlib.pyplot as plt\n# sklearn.tree 모듈에서 plot_tree 함수 가져오기\nfrom sklearn.tree import plot_tree\nplt.figure(figsize=(20, 10)) # 이미지 크기(20, 10) 설정하기\nplot_tree(dt, feature_names=X.columns,\n           max_depth=2, filled=True)\nplt.show()\n")
        elif ct == "code" and "dt 모델 예측하기" in t:
            set_code(cell, "dt_pred = dt.predict(X_test)                  # dt 모델 예측하기\n# 테스트 데이터로 결정트리 모델 분류 정확도 구하기\nprint(\"결정트리 모델 성능 평가 : \", dt.score(X_test, y_test))\n")
        elif ct == "code" and not t.strip():
            empties.append(i)
        elif ct == "markdown" and "데이터가 모두 몇 개 있는가?" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 이 데이터에는 데이터가 모두 몇 개 있는가?  → **344개**\n- 결측치가 있는 속성은 무엇이고, 각각 몇 개인가?\n\n  → **교과서: 종·서식지는 344개, 나머지 일부 열은 342개 또는 334개.**\n")
        elif ct == "markdown" and "344개에서 334개로 줄었다" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 데이터가 344개에서 334개로 줄었다. 결측치 때문에 삭제된 데이터는 몇 개인가?  → **10개**\n- 결측치가 있는 데이터를 삭제한 이유는 무엇인가?\n\n  → **결측치는 모델 성능을 떨어뜨리는 요인이기 때문이다.**\n")
        elif ct == "markdown" and "근거로 사용할 특징은 무엇인가?" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 모델이 펭귄 종을 분류할 때 근거로 사용할 특징은 무엇인가?\n\n  → **culmen_length_mm(부리 길이), culmen_depth_mm(부리 깊이), flipper_length_mm(날개 길이)**\n- 모델이 맞혀야 할 타깃은 무엇인가?  → **species(펭귄 종)**\n- 이 문제는 연속적인 값을 예측하는 회귀인가, 종류를 맞히는 분류인가?  → **분류**\n")
        elif ct == "markdown" and "훈련 데이터와 테스트 데이터는 각각 몇 개인가?" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 훈련 데이터와 테스트 데이터는 각각 몇 개인가?  → 훈련 **233개** · 테스트 **101개**\n- `stratify=y`를 사용하면 어떤 효과가 있는가?\n\n  → **펭귄 종을 훈련/테스트에 균일하게 나눈다.**\n")
        elif ct == "markdown" and "훈련 데이터에 대한 정확도는 약 얼마인가?" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 훈련 데이터에 대한 정확도는 약 얼마인가?  → **1.0**\n- 훈련 정확도 1.00만 보고 새로운 펭귄도 모두 맞힐 것이라고 판단해도 될까?\n\n  → **아니다. 테스트 데이터로 다시 평가해야 한다.**\n")
        elif ct == "markdown" and "가장 먼저 사용한 특징은 무엇인가?" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 트리의 맨 위(루트 노드)에서 가장 먼저 사용한 특징은 무엇인가?  → **flipper_length_mm(날개 길이)**\n- 그 특징의 기준값(threshold)은 대략 얼마인가?  → **206.5 mm**\n")
        elif ct == "markdown" and "테스트 데이터에 대한 정확도는 약 얼마인가?" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 테스트 데이터에 대한 정확도는 약 얼마인가?  → **`dt.score(X_test, y_test)` 실행 결과**\n- 훈련 정확도와 테스트 정확도를 비교해 보자. 차이가 있는가?\n\n  → **있을 수 있다. 훈련은 1.0이고 테스트는 그보다 낮으면 과적합을 의심한다.**\n")
        elif ct == "markdown" and "🏁 마무리" in t:
            set_md(cell, "## 🏁 마무리\n\n1. 루트 노드에서 가장 먼저 사용한 특징은 무엇인가?\n\n   → **날개 길이(flipper_length_mm), 기준값 206.5 mm**\n\n2. 훈련 정확도와 테스트 정확도가 다른 이유는 무엇인가?\n\n   → **훈련은 학습한 데이터, 테스트는 처음 보는 데이터에 대한 성능이다.**\n\n3. 이 모델을 실제 생태 조사에 활용한다면 어떤 점에 주의해야 할까?\n\n   → **측정 오차, 지역·계절 차이, 데이터 편향을 보고 추가 검증 없이 단정하지 않는다.**\n")
    codes = [
        "X = df[['culmen_length_mm', 'culmen_depth_mm',\n        'flipper_length_mm']]\ny = df['species']\n",
        "from sklearn.model_selection import train_test_split\nX_train, X_test, y_train, y_test = train_test_split(\n                            X, y, test_size=0.3, stratify=y)\n",
    ]
    for i, code in zip(empties, codes):
        set_code(nb["cells"][i], code)


def fill_s4(nb):
    empties = []
    for i, cell in enumerate(nb["cells"]):
        t = join(cell)
        ct = cell.get("cell_type")
        if ct == "code" and "pandas 불러오기" in t:
            set_code(cell, "import pandas as pd                            # pandas 불러오기\ndf = pd.read_csv('Mall_Customers.csv')\ndf.head()\n")
        elif ct == "code" and "데이터 프레임 5행 보여 주기" in t:
            set_code(cell, "data = df[['Annual Income (k$)', 'Spending Score (1-100)']]\ndata.head()                                # 데이터 프레임 5행 보여 주기\n")
        elif ct == "code" and "k = 5인 KMeans" in t:
            set_code(cell, "from sklearn.cluster import KMeans\nk = 5\nmodel = KMeans(n_clusters=k)     # k = 5인 KMeans 모델을 생성하기\nmodel.fit(data)                  # 군집 모델을 학습하기\n")
        elif ct == "code" and "데이터 군집 예측하기" in t:
            set_code(cell, "prediction = model.predict(data)            # 데이터 군집 예측하기\nprediction[0:10]                            # 어떤 군집에 속하는지 보여 주기\n# 군집 결과를 df['centroid'] 열에 추가하기\ndf['centroid'] = model.labels_\n# 군집의 중심값을 반환해 final_centroid에 저장하기\nfinal_centroid = model.cluster_centers_\nprint(final_centroid)\n")
        elif ct == "code" and "산점도에 표시하기" in t:
            set_code(cell, "import seaborn as sns\nimport matplotlib.pyplot as plt\n# Annual Income (k$)과 Spending Score (1-100)를 산점도에 표시하기\nsns.scatterplot(x='Annual Income (k$)',\n                  y='Spending Score (1-100)', hue='centroid',\n                  data=df, palette='bright')\n# final_centroid에 저장된 군집 중심값을 산점도에 표시하기\nplt.scatter(final_centroid[:, 0], final_centroid[:, 1],\nmarker='*', s=300, color='black', label='Centroids')\nplt.legend() # 범례 표시하기\nplt.show()\n")
        elif ct == "code" and "실루엣 계산" in t:
            set_code(cell, "from sklearn.metrics import silhouette_score          # 실루엣 계산\nsilhouette = silhouette_score(data, model.labels_)\nprint(silhouette)\n")
        elif ct == "code" and not t.strip():
            empties.append(i)
        elif ct == "markdown" and "고객이 모두 몇 명 있는가?" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 이 데이터에는 고객이 모두 몇 명 있는가?  → **200명**\n- 데이터의 속성(열)은 몇 개인가?  → **5개**\n- 결측치가 있는 속성이 있는가?  → **없다**\n")
        elif ct == "markdown" and "특징(data)은 몇 개인가?" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 군집에 사용할 특징(data)은 몇 개인가?  → **2개** (연 소득, 소비 점수)\n- 군집 분석에는 왜 타깃 y가 필요 없는가?\n\n  → **군집 모델은 타깃이 필요 없다. 비지도학습이기 때문이다.**\n")
        elif ct == "markdown" and "군집 중심점이 5개인 이유" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 군집 중심점이 5개인 이유는 무엇인가?  → **k=5로 설정했기 때문이다.**\n- 각 중심점의 두 값은 무엇을 나타내는가?\n\n  → **해당 군집의 평균 연 소득과 평균 소비 점수**\n- 군집 번호가 크다고 더 좋은 군집이라는 뜻인가?  → **아니다. 번호는 이름표일 뿐이다.**\n")
        elif ct == "markdown" and "검은 별표" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 산점도에서 검은 별표(중심점)는 무엇을 나타내는가?\n\n  → **각 군집의 중심(평균 연 소득, 평균 소비 점수)**\n- 소득도 소비 점수도 모두 높은 군집은 어디에 위치하는가? (오른쪽 위 / 오른쪽 아래 / 왼쪽 위 / 왼쪽 아래)  → **오른쪽 위**\n")
        elif ct == "markdown" and "k=5일 때 실루엣 점수" in t:
            set_md(cell, "**❓ 확인하기**\n\n- k=5일 때 실루엣 점수는 약 얼마인가?  → **약 0.5539**\n- 이 점수가 0보다 크고 1에 더 가까운 것은 군집 결과에 대해 무엇을 뜻하는가?\n\n  → **데이터가 자기 군집에 어느 정도 잘 속해 있다는 뜻이다.**\n- k=5가 가장 적절한지는 어떻게 더 확인할 수 있을까?\n\n  → **k를 바꿔 가며 실루엣 점수를 비교한다.**\n")
        elif ct == "markdown" and "실루엣 점수가 가장 높은 k" in t:
            set_md(cell, "**❓ 확인하기**\n\n- 실루엣 점수가 가장 높은 k는 얼마인가?  → **보통 5**\n- 그 점수는 교과서에서 사용한 k=5의 점수와 비교했을 때 어떠한가?\n\n  → **교과서 k=5 실루엣은 약 0.5539이다. 비슷하면 5가 적절하다.**\n")
        elif ct == "markdown" and "🏁 마무리" in t:
            set_md(cell, "## 🏁 마무리\n\n1. 지도학습과 달리 군집 모델에 타깃 y가 필요 없는 이유는 무엇인가?\n\n   → **군집은 정답이 없는 비지도학습이라 비슷한 특성끼리 묶는 것이 목표이다.**\n\n2. 군집 0~4의 고객 특성을 연 소득과 소비 점수로 설명해 보자.\n\n   → **고소득·고소비(오른쪽 위), 고소득·저소비(오른쪽 아래), 저소득·고소비(왼쪽 위), 저소득·저소비(왼쪽 아래), 중간·중간.**\n\n3. 실루엣 점수가 가장 높은 k와 교과서의 k=5 결과를 비교해 보자.\n\n   → **교과서 k=5 실루엣은 약 0.5539이다. 가장 높은 k가 5 근처이면 같다.**\n")
    extra = (
        "from sklearn.cluster import KMeans\n"
        "from sklearn.metrics import silhouette_score\n"
        "ks = range(2, 9)\n"
        "scores = []\n"
        "for k in ks:\n"
        "    m = KMeans(n_clusters=k)\n"
        "    labels = m.fit_predict(data)\n"
        "    scores.append((k, silhouette_score(data, labels)))\n"
        "print(scores)\n"
        "print('best k:', max(scores, key=lambda x: x[1]))\n"
    )
    for i in empties[:1]:
        set_code(nb["cells"][i], extra)


HANDLERS = {
    "실습3_펭귄_종_분류_모델_구현하기.ipynb": fill_s3,
    "실습4_쇼핑몰_고객_군집_모델_구현하기.ipynb": fill_s4,
}


def main() -> None:
    for student in sorted(ROOT.rglob("*.ipynb")):
        if "_정답" in student.name or "jlite" in student.parts:
            continue
        if student.name not in HANDLERS:
            continue
        nb = json.loads(student.read_text(encoding="utf-8"))
        HANDLERS[student.name](nb)
        out = student.with_name(student.stem + "_정답.ipynb")
        out.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
