# rirekisyo_photo

履歴書用の証明写真を作成するためのスクリプトです。

入力画像から顔位置を検出し、背景を白系に変換したうえで、履歴書用写真サイズの PNG を出力します。

---

## できること

- JPG画像を入力にする
- 顔の位置を自動検出する
- 顔位置を基準に履歴書用サイズへトリミングする
- `rembg` で背景を透過処理する
- 白系背景を合成する
- PNG形式で出力する
- 出力ファイル名に timestamp を自動付与する
- 入出力ファイル名や調整値を `config.def` で管理する

---

## ディレクトリ構成

```text
rirekisyo_photo/
├── convert.py
├── config.def
├── requirements.txt
├── README.md
├── .gitignore
├── data/
│   └── input.jpg
├── .output/
│   └── rirekisyo_YYYYMMDD_HHMMSS.png
└── bk/
```

---

## Git管理対象

基本的にGitに上げるもの:

```text
convert.py
config.def
requirements.txt
README.md
.gitignore
```

Gitに上げないもの:

```text
data/
.output/
bk/
.venv/
__pycache__/
*Zone.Identifier
```

入力写真や生成画像は個人情報を含むため、Git管理対象から外します。

---

## 初回セットアップ

Python仮想環境を作成します。

```bash
python -m venv .venv
```

仮想環境を有効化します。

```bash
source .venv/bin/activate
```

pipを更新します。

```bash
python -m pip install --upgrade pip
```

必要なライブラリをインストールします。

```bash
pip install -r requirements.txt
```

`requirements.txt` がない場合は、最低限以下を入れます。

```bash
pip install pillow opencv-python rembg onnxruntime numpy
```

GPU版の `onnxruntime-gpu` は不要です。証明写真1枚の処理ではCPU版で足ります。

---

## onnxruntime CUDAエラーが出た場合

以下のようなエラーが出る場合があります。

```text
Failed to load library ... libonnxruntime_providers_cuda.so
libcublasLt.so.12: cannot open shared object file
```

この場合、CUDA実行基盤が不足している状態です。GPU版ではなくCPU版へ戻します。

```bash
pip uninstall -y onnxruntime-gpu onnxruntime
pip install onnxruntime
```

`rembg` も含めて入れ直す場合:

```bash
pip uninstall -y rembg onnxruntime-gpu onnxruntime
pip install rembg onnxruntime
```

---

## 入力画像の配置

入力画像は `data/` 配下に置きます。

例:

```text
data/input.jpg
```

`data/` は `.gitignore` で除外します。

---

## 設定ファイル

設定は `config.def` に記載します。

```ini
[app]
input_path = ./data/input.jpg
output_dir = .output
output_basename = rirekisyo


[photo]
output_size = 354,472
dpi = 300
background_color = 250,250,248,255
face_height_ratio = 0.48
face_center_y_ratio = 0.42


[face_detection]
scale_factor = 1.1
min_neighbors = 5
min_size = 80,80
```

---

## 設定値の意味

### `[app]`

#### `input_path`

入力画像のパスです。

```ini
input_path = ./data/input.jpg
```

#### `output_dir`

出力先ディレクトリです。

```ini
output_dir = .output
```

#### `output_basename`

出力ファイル名の先頭部分です。

```ini
output_basename = rirekisyo
```

実際の出力名は以下の形式になります。

```text
.output/rirekisyo_YYYYMMDD_HHMMSS.png
```

---

### `[photo]`

#### `output_size`

出力画像サイズです。

履歴書用写真は一般的に横3cm × 縦4cmです。

300dpiの場合:

```ini
output_size = 354,472
```

対応関係:

```text
横3cm ≒ 354px
縦4cm ≒ 472px
```

#### `dpi`

出力PNGに付与するdpi情報です。

```ini
dpi = 300
```

#### `background_color`

背景色です。

```ini
background_color = 250,250,248,255
```

形式:

```text
R,G,B,A
```

完全な白にする場合:

```ini
background_color = 255,255,255,255
```

少しだけ白系にする場合:

```ini
background_color = 250,250,248,255
```

#### `face_height_ratio`

出力画像の高さに対して、検出された顔の高さをどの程度にするかを指定します。

```ini
face_height_ratio = 0.48
```

顔が大きすぎる場合:

```ini
face_height_ratio = 0.44
```

顔が小さすぎる場合:

```ini
face_height_ratio = 0.52
```

#### `face_center_y_ratio`

顔の中心を切り抜き範囲の上から何%の位置に置くかを指定します。

```ini
face_center_y_ratio = 0.42
```

顔が上すぎる場合:

```ini
face_center_y_ratio = 0.46
```

顔が下すぎる場合:

```ini
face_center_y_ratio = 0.38
```

---

### `[face_detection]`

OpenCV Haar Cascade の顔検出設定です。

通常は変更不要です。

```ini
scale_factor = 1.1
min_neighbors = 5
min_size = 80,80
```

顔が検出されない場合、`min_size` を小さくすると検出される場合があります。

```ini
min_size = 60,60
```

ただし、小さくしすぎると誤検出が増えます。

---

## 実行方法

仮想環境を有効化します。

```bash
source .venv/bin/activate
```

実行します。

```bash
python convert.py
```

出力例:

```text
saved: .output/rirekisyo_20260609_145500.png
```

---

## 処理の流れ

```text
入力JPG
  ↓
EXIF回転補正
  ↓
顔位置検出
  ↓
rembgで背景透過
  ↓
白系背景を合成
  ↓
顔位置を基準に3:4でトリミング
  ↓
354px × 472pxへリサイズ
  ↓
PNG保存
```

---

## 調整手順

1. `data/` に入力画像を置く
2. `config.def` の `input_path` を変更する
3. `python convert.py` を実行する
4. `.output/` の画像を確認する
5. 顔の大きさや位置がズレていたら `config.def` を調整する

調整する主な値:

```ini
face_height_ratio = 0.48
face_center_y_ratio = 0.42
```

顔の大きさだけ直す場合:

```ini
face_height_ratio = 0.44
```

または:

```ini
face_height_ratio = 0.52
```

顔の上下位置だけ直す場合:

```ini
face_center_y_ratio = 0.38
```

または:

```ini
face_center_y_ratio = 0.46
```

---

## 注意点

- 顔が横向き、暗い、髪で隠れている、顔が小さい場合は顔検出に失敗することがあります。
- 背景透過は `rembg` の推論結果に依存します。
- 履歴書用として使う場合、最終的な見た目は手動確認が必要です。
- `data/` と `.output/` はGitに含めない構成です。
- PNG出力ですが、背景は白系で合成済みなので透過PNGではありません。

---

## 最小コマンド再掲

```bash
source .venv/bin/activate
python convert.py
```
