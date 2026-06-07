# カードPDF生成 ドキュメント

## 概要

このディレクトリは、FigmaのカードデザインをPython + PillowでPDF化する生成ツールです。カードの見た目はテンプレートに固定し、JSONやWebフォーム/APIから文字だけを差し替えて使います。

Docker ComposeでWebサーバーを起動すると、`localhost:8080` からフォーム操作とAPI利用の両方ができます。プリンターへの直接送信は行わず、Docker内ではPDF生成までを担当します。

## 全体構成

- `main.py`: PDF生成、テンプレート定義、CLI、Web/APIサーバー
- `docker-compose.yml`: `localhost:8080` 起動設定
- `Dockerfile`: Python + 依存ライブラリのコンテナ定義
- `requirements.txt`: `Pillow` と `Flask`
- `font/`: 必須フォント置き場
- `assets/`: Figma由来の背景・キャラ・共通画像
- `examples/`: 入力JSONサンプル
- `output/`: 生成PDF・確認用PNGの出力先
- `docs/`: この仕様ドキュメント

## 必須フォント

以下を配置します。

- `font/x8y12pxDenkiChip.ttf`
- `font/x10y12pxDonguriDuel.ttf` または `.otf`

`x10y12pxDonguriDuel` が無い場合は通常エラーになります。検証用にだけ `--allow-font-fallback` を付けるとx8フォントで代替できます。

## 入力JSON

最小入力はテンプレートだけです。文字を省略するとテンプレートの既定値が使われます。

```json
{
  "template": "gonta"
}
```

文字やフォントサイズを指定する例:

```json
{
  "template": "gonta",
  "name": "ごんた",
  "attribute": "ほのお",
  "skill": "ほのお",
  "skill_font_size": 50,
  "phrase": "ガオー",
  "phrase_font_size": 60,
  "habitat": "かざん",
  "habitat_font_size": 65,
  "description": "あつい場所がすき。",
  "hp": "30"
}
```

複数ページPDFは `cards` 配列を使います。

```json
{
  "cards": [
    {"template": "slime"},
    {"template": "shibazou"},
    {"template": "gonta"}
  ]
}
```

## 指定できる主な項目

- `template`: テンプレートID。省略時は `slime`
- `name`: カード名
- `attribute`: 属性表示
- `skill`: とくぎ欄の内容
- `skill_font_size`: とくぎ欄のフォントサイズ、20から128
- `phrase`: くちぐせ欄の内容
- `phrase_font_size`: くちぐせ欄のフォントサイズ、20から128
- `habitat`: せいそくち欄の内容
- `habitat_font_size`: せいそくち欄のフォントサイズ、20から128
- `description`: 説明文
- `hp`: HP値。描画時は `HP:{hp}` になります
- `skill_label`: `とくぎ` ラベル自体の差し替え
- `phrase_label`: `くちぐせ` ラベル自体の差し替え
- `habitat_label`: `せいそくち` ラベル自体の差し替え
- `background_image`: 背景画像を差し替えるパス
- `character_image`: キャラ画像を差し替えるパス

## 文字数制限

フォントサイズはFigmaの指定を基本にし、自動縮小はしません。長すぎる文字はエラーにします。

標準テンプレート:

- `name`: 6文字以内
- `attribute`: 4文字以内
- `skill`: 8文字以内
- `phrase`: 12文字以内
- `habitat`: 7文字以内
- `hp`: 4文字以内
- `description`: 改行を除いて52文字以内

`mojaokun` テンプレート:

- `phrase`: 18文字以内
- `description`: 改行を除いて92文字以内
- その他は標準テンプレートと同じ

## 関連ドキュメント

- [API.md](API.md): HTTP APIの詳細
- [TEMPLATES.md](TEMPLATES.md): 8テンプレートの一覧
- [ASSETS.md](ASSETS.md): Figmaアセット管理と重複排除
## テンプレートJSON管理

テンプレートはコード内ではなく、リポジトリ直下の `templates.json` から読み込まれます。`main.py` は起動時にJSONを読み、`CardTemplate` に変換してCLI/API/Webフォームで共通利用します。
