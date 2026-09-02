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


def fill_by_index(nb, codes):
    cells = nb["cells"]
    for i, text in codes.items():
        if i < len(cells) and cells[i].get("cell_type") == "code":
            set_code(cells[i], text)


def fill_s5(nb):
    fill_by_index(nb, {
        6: "from tensorflow import keras\n\nmnist = keras.datasets.mnist\n(X_train, y_train), (X_test, y_test) = mnist.load_data()\nprint(X_train.shape, y_train.shape, X_test.shape, y_test.shape)\n",
        9: "import matplotlib.pyplot as plt\n\nimage = X_test[0].reshape(28, 28)\nplt.imshow(image, cmap='gray')\nplt.title(y_test[0])\nplt.show()\n",
        12: "X_train = X_train / 255.0\nX_test = X_test / 255.0\n",
        14: "from tensorflow.keras.models import Sequential\nfrom tensorflow.keras.layers import Dense, Flatten\n",
        16: "model = Sequential()\nmodel.add(Flatten(input_shape=(28, 28)))\nmodel.add(Dense(128, activation='relu'))\n",
        17: "model.add(Dense(64, activation='relu'))\nmodel.add(Dense(10, activation='softmax'))\n",
        19: "model.compile(\n    loss='sparse_categorical_crossentropy',\n    optimizer='adam',\n    metrics=['accuracy']\n)\n",
        21: "model.fit(X_train, y_train, epochs=10)\n",
        25: "model.evaluate(X_test, y_test)\n",
        28: "predictions = model.predict(X_test)\nprint(predictions[0])\n",
        31: "import numpy as np\n\nprint(np.argmax(predictions[0]))\n",
        34: "model.save(\"mnist_model.h5\")\n",
    })
    cells = nb["cells"]
    reps = {
        7: [("훈련 ( )개 · 테스트 ( )개", "훈련 **60000**개 · 테스트 **10000**개"), ("  → ( )", "  → **숫자 한 장이 세로 28픽셀, 가로 28픽셀이라는 뜻이다.**"), ("  → ( )", "  → **테스트 이미지 한 장을 그림으로 확인한다.**")],
        10: [("→ ( )", "→ **7** (`y_test[0]`)"), ("→ ( )", "→ **일치한다.**"), ("  → ( )", "  → **0~1 사이로 정규화한다.**")],
        22: [("→ ( )", "→ **줄어든다.** (교과서 예: 0.2387 → 0.0198)"), ("→ ( )", "→ **높아진다.** (교과서 예: 0.9284 → 0.9934)"), ("  → ( )", "  → **안 된다. 테스트 데이터로 다시 평가해야 한다.**")],
        26: [("손실 ( ) · 정확도 ( )", "손실 **0.0955** · 정확도 **0.9784**"), ("  → ( )", "  → **배우지 않은 데이터에서는 성능이 조금 떨어질 수 있다.**"), ("  → ( )", "  → **한 장이 어떤 숫자로 예측되는지 본다.**")],
        29: [("→ ( )개", "→ **10**개"), ("→ ( )", "→ **7번**"), ("→ ( )", "→ **np.argmax()**")],
        32: [("→ ( )", "→ **7**"), ("→ ( )", "→ **일치한다.**"), ("→ ( )", "→ **모델을 파일로 저장한다.**")],
        36: [("   →\n", "   → **28×28 픽셀, 출력층 10개(숫자 0~9)**\n"), ("   →\n", "   → **테스트 정확도가 약 0.978로 높아서 대체로 잘 분류한다.**\n"), ("   →\n", "   → **소프트맥스 확률 중 7번 인덱스 값이 가장 크기 때문이다.**\n")],
    }
    for i, pairs in reps.items():
        text = join(cells[i])
        for old, new in pairs:
            text = text.replace(old, new, 1)
        set_md(cells[i], text)


def fill_s6(nb):
    fill_by_index(nb, {
        7: "import os\nfrom pathlib import Path\n\ntry:\n    from google.colab import drive\nexcept ImportError:\n    current_dir = Path.cwd()\n    data_dir = current_dir if current_dir.name == 'crack' else current_dir / 'crack'\nelse:\n    drive.mount('/content/gdrive')\n    data_dir = Path('/content/gdrive/My Drive/data/crack')\n    if not (data_dir / 'train').is_dir():\n        alt = Path('/content/gdrive/MyDrive/data/crack')\n        if (alt / 'train').is_dir():\n            data_dir = alt\n\nos.chdir(data_dir)\nprint('현재 폴더:', Path.cwd())\n",
        9: "from tensorflow.keras.preprocessing.image import ImageDataGenerator\n\ntrain_datagen = ImageDataGenerator(rescale=1./255)\ntraining_set = train_datagen.flow_from_directory(\n    'train',\n    target_size=(64, 64),\n    batch_size=32,\n    shuffle=True,\n    class_mode='categorical'\n)\n",
        12: "test_datagen = ImageDataGenerator(rescale=1./255)\ntest_set = test_datagen.flow_from_directory(\n    'test',\n    target_size=(64, 64),\n    shuffle=False,\n    class_mode='categorical'\n)\n",
        16: "from tensorflow.keras.applications.vgg16 import VGG16\n\nvgg = VGG16(include_top=False, weights='imagenet', input_shape=(64, 64, 3))\nfor layer in vgg.layers:\n    layer.trainable = False\nvgg.summary()\n",
        19: "from tensorflow.keras.models import Sequential\nfrom tensorflow.keras.layers import Dense, Flatten, Input\n",
        21: "model = Sequential()\nmodel.add(Input(shape=(64, 64, 3)))\nmodel.add(vgg)\nmodel.add(Flatten())\nmodel.add(Dense(64, activation='relu'))\nmodel.add(Dense(2, activation='softmax'))\nmodel.summary()\n",
        24: "model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])\n",
        26: "model.fit(training_set, epochs=5)\n",
        30: "model.evaluate(test_set)\n",
        33: "pred = model.predict(test_set)\nprint(pred[:3])\n",
        35: "print(training_set.class_indices)\n",
        38: "import numpy as np\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nfrom sklearn.metrics import confusion_matrix\n\nPredicted = np.argmax(pred, axis=1)\nActual = test_set.labels\nconf = confusion_matrix(Actual, Predicted)\n\nsns.heatmap(conf, annot=True, cmap='BuPu', fmt='d')\nplt.title('Crack Classification')\nplt.xlabel('Predicted')\nplt.ylabel('Actual')\nplt.show()\n",
    })
    cells = nb["cells"]
    reps = {
        10: [("→ ( )개", "→ **300**개"), ("→ ( )개", "→ **2**개 (Negative, Positive)"), ("→ ( )", "→ **테스트 데이터**")],
        13: [("→ ( )개", "→ **80**개"), ("  → ( )", "  → **예측 결과와 실제 레이블 순서를 맞춰 혼동 행렬을 만들기 위해서이다.**"), ("→ ( )", "→ **특징(feature)**")],
        17: [("→ `( )`", "→ 입력 64×64일 때 보통 **(None, 2, 2, 512)**"), ("  → ( )", "  → **사전 학습된 가중치를 고정(`trainable=False`)했기 때문이다.**"), ("→ ( )", "→ **완전 연결 계층(Dense)**")],
        22: [("  → ( )", "  → **Negative / Positive 두 클래스를 분류하기 때문이다.**"), ("  → ( )", "  → **뒤에 붙인 Flatten·Dense 층**"), ("→ ( )", "→ **손실함수·최적화 함수·평가지표(compile)**")],
        27: [("  → ( )", "  → **손실은 줄고 정확도는 높아진다.**"), ("  → ( )", "  → **아니다. 테스트 데이터로 따로 평가해야 한다.**")],
        31: [("→ ( )", "→ 교과서 예: 손실 **약 0.18** · 정확도 **0.9125**"), ("→ ( )", "→ **과적합**"), ("  → ( )", "  → **알 수 없다. 혼동 행렬이 필요하다.**")],
        36: [("Negative ( ) · Positive ( )", "Negative **0** · Positive **1**"), ("→ ( )", "→ **혼동 행렬**")],
        39: [("→ ( )", "→ **정확히 분류한 개수**"), ("40 + 33 = ( )개", "40 + 33 = **73**개"), ("  → ( )", "  → **실제 Positive 7장을 Negative로 잘못 분류한 것**")],
        40: [("   →\n", "   → **훈련 300개, 테스트 80개. Negative / Positive**\n"), ("   →\n", "   → **ImageNet으로 미리 배운 특징 추출기를 그대로 쓰고, 데이터가 적을 때 과적합을 줄이기 위해서이다.**\n"), ("   →\n", "   → **전체 정확도만으로는 어느 클래스를 자주 틀리는지 알 수 없기 때문이다.**\n"), ("   →\n", "   → **균열 있음(Positive)을 균열 없음으로 놓치는 경우**\n")],
    }
    for i, pairs in reps.items():
        text = join(cells[i])
        for old, new in pairs:
            text = text.replace(old, new, 1)
        set_md(cells[i], text)


def fill_s3(nb):
    empties = []
    for i, cell in enumerate(nb["cells"]):
        t = join(cell)
        ct = cell.get("cell_type")
        if ct == "code" and "데이터 프레임 요약 정보" in t and "dropna" not in t:
            set_code(cell, "import pandas as pd\ndf = pd.read_csv('penguins_size.csv')\ndf.info()\n")
        elif ct == "code" and "결측치 개수 확인하기" in t:
            set_code(cell, "df.isnull().sum()\ndf.dropna(axis=0, inplace=True)\ndf.info()\n")
        elif ct == "code" and "모델 생성하기" in t:
            set_code(cell, "from sklearn.tree import DecisionTreeClassifier\ndt = DecisionTreeClassifier()\ndt.fit(X_train, y_train)\nprint(dt.score(X_train, y_train))\n")
        elif ct == "code" and "plot_tree" in t:
            set_code(cell, "import matplotlib.pyplot as plt\nfrom sklearn.tree import plot_tree\nplt.figure(figsize=(20, 10))\nplot_tree(dt, feature_names=X.columns, max_depth=2, filled=True)\nplt.show()\n")
        elif ct == "code" and "dt 모델 예측하기" in t:
            set_code(cell, "dt_pred = dt.predict(X_test)\nprint(\"결정트리 모델 성능 평가 : \", dt.score(X_test, y_test))\n")
        elif ct == "code" and not t.strip():
            empties.append(i)
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
            set_code(cell, "import pandas as pd\ndf = pd.read_csv('Mall_Customers.csv')\ndf.head()\n")
        elif ct == "code" and "데이터 프레임 5행 보여 주기" in t:
            set_code(cell, "data = df[['Annual Income (k$)', 'Spending Score (1-100)']]\ndata.head()\n")
        elif ct == "code" and "k = 5인 KMeans" in t:
            set_code(cell, "from sklearn.cluster import KMeans\nk = 5\nmodel = KMeans(n_clusters=k)\nmodel.fit(data)\n")
        elif ct == "code" and "데이터 군집 예측하기" in t:
            set_code(cell, "prediction = model.predict(data)\nprediction[0:10]\ndf['centroid'] = model.labels_\nfinal_centroid = model.cluster_centers_\nprint(final_centroid)\n")
        elif ct == "code" and "산점도에 표시하기" in t:
            set_code(cell, "import seaborn as sns\nimport matplotlib.pyplot as plt\nsns.scatterplot(x='Annual Income (k$)',\n                  y='Spending Score (1-100)', hue='centroid',\n                  data=df, palette='bright')\nplt.scatter(final_centroid[:, 0], final_centroid[:, 1],\nmarker='*', s=300, color='black', label='Centroids')\nplt.legend()\nplt.show()\n")
        elif ct == "code" and "실루엣 계산" in t:
            set_code(cell, "from sklearn.metrics import silhouette_score\nsilhouette = silhouette_score(data, model.labels_)\nprint(silhouette)\n")
        elif ct == "code" and not t.strip():
            empties.append(i)
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
    "실습53_펭귄_종_분류_모델_구현하기.ipynb": fill_s3,
    "실습54_쇼핑몰_고객_군집_모델_구현하기.ipynb": fill_s4,
    "실습55_손으로_쓠_숫자_분류_모델_구현하기.ipynb": fill_s5,
    "실습56_도로_균열_유무를_분류하는_합성곱_신경망_모델_구현하기.ipynb": fill_s6,
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
        print("wrote", out.relative_to(ROOT), "cells", len(nb["cells"]))


if __name__ == "__main__":
    main()
