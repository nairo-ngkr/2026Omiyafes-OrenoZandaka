# APIドキュメント

## 概要

カードPDF生成サーバーは、JSONを受け取り、Figma由来テンプレートを使ってPDFを返します。Webフォームと同じ生成処理をAPIから利用できます。

## 起動

```bash
cd /Users/nono/Documents/GitHub/print-unity-ofes2026/gen-print/gen-png
docker compose build
docker compose up
```

ベースURL:

```text
http://localhost:8080/api/v1
```

## エンドポイント一覧

| Method | Path | 内容 |
|---|---|---|
| `GET` | `/api/v1/` | API情報とテンプレートID一覧を返す |
| `GET` | `/api/v1/health` | ヘルスチェック |
| `GET` | `/api/v1/templates` | テンプレート詳細一覧を返す |
| `POST` | `/api/v1/generate` | JSONからPDFを生成する |

## GET `/api/v1/health`

サーバーの疎通確認用です。

```bash
curl http://localhost:8080/api/v1/health
```

レスポンス:

```json
{
  "ok": true
}
```

## GET `/api/v1/`

API情報と利用可能なテンプレートID一覧を返します。

```bash
curl http://localhost:8080/api/v1/
```

レスポンス例:

```json
{
  "ok": true,
  "endpoints": {
    "GET /api/v1/": "API情報",
    "GET /api/v1/health": "ヘルスチェック",
    "GET /api/v1/templates": "テンプレート一覧",
    "POST /api/v1/generate": "PDF生成"
  },
  "templates": ["slime", "shibazou", "gonta"]
}
```

## GET `/api/v1/templates`

テンプレートの詳細を返します。クライアント側でテンプレート選択UIを作る場合は、このAPIを使います。

```bash
curl http://localhost:8080/api/v1/templates
```

テンプレート1件の形式:

```json
{
  "id": "gonta",
  "label": "ごんた",
  "figma_node": "162:339",
  "defaults": {
    "name": "ごんた",
    "attribute": "ぞくせい",
    "skill": "きらきらさがし",
    "phrase": "「○○ぽよ」",
    "habitat": "わくせい",
    "description": "せんとうちゅう でもカメラ目線をわすれない。\nなぜか集合写真には必ず写っている。",
    "hp": "30"
  },
  "default_font_sizes": {
    "skill_font_size": 57,
    "phrase_font_size": 75,
    "habitat_font_size": 75
  },
  "limits": {
    "name": 6,
    "attribute": 4,
    "skill": 8,
    "phrase": 12,
    "habitat": 7,
    "hp": 4,
    "description": 52
  }
}
```

## POST `/api/v1/generate`

カードPDFを生成します。成功時はJSONではなくPDFバイナリを返します。

リクエストヘッダー:

```http
Content-Type: application/json
```

レスポンス:

```http
Content-Type: application/pdf
```

### 単一カード生成

```bash
curl -X POST http://localhost:8080/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"template":"gonta"}' \
  --output output/gonta.pdf
```

文字を上書きする例:

```bash
curl -X POST http://localhost:8080/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "template": "gonta",
    "name": "ごんた",
    "attribute": "ほのお",
    "skill": "ひのこ",
    "skill_font_size": 50,
    "phrase": "ガオー",
    "phrase_font_size": 60,
    "habitat": "かざん",
    "habitat_font_size": 65,
    "description": "あつい場所がすき。",
    "hp": "30"
  }' \
  --output output/gonta-custom.pdf
```

### 複数ページPDF生成

`cards` 配列を送ると、1つのPDFに複数ページとして出力します。

```bash
curl -X POST http://localhost:8080/api/v1/generate \
  -H "Content-Type: application/json" \
  -d @examples/cards.json \
  --output output/cards.pdf
```

リクエスト例:

```json
{
  "cards": [
    {"template": "slime"},
    {"template": "gonta", "name": "ごんた"},
    {"template": "kukuros", "skill": "ひとつめ"}
  ]
}
```

## リクエストJSON仕様

単一カードの場合は、以下のフィールドをトップレベルに指定します。複数ページの場合は、同じ形式のオブジェクトを `cards` 配列に入れます。

| フィールド | 型 | 必須 | 内容 |
|---|---|---|---|
| `template` | string | 任意 | テンプレートID。省略時は `slime` |
| `name` | string | 任意 | カード名。省略時はテンプレート既定値 |
| `attribute` | string | 任意 | 属性。省略時はテンプレート既定値 |
| `skill` | string | 任意 | とくぎ欄の内容 |
| `skill_font_size` | number | 任意 | とくぎ欄フォントサイズ。20から128 |
| `phrase` | string | 任意 | くちぐせ欄の内容 |
| `phrase_font_size` | number | 任意 | くちぐせ欄フォントサイズ。20から128 |
| `habitat` | string | 任意 | せいそくち欄の内容 |
| `habitat_font_size` | number | 任意 | せいそくち欄フォントサイズ。20から128 |
| `description` | string | 任意 | 説明文 |
| `hp` | string/number | 任意 | HP値。描画時は `HP:{hp}` |
| `skill_label` | string | 任意 | `とくぎ` ラベルの差し替え |
| `phrase_label` | string | 任意 | `くちぐせ` ラベルの差し替え |
| `habitat_label` | string | 任意 | `せいそくち` ラベルの差し替え |
| `background_image` | string | 任意 | 背景画像パス |
| `character_image` | string | 任意 | キャラ画像パス |

## テンプレートID

現在利用できるテンプレート:

- `slime`
- `patasan`
- `gonta`
- `mojaokun`
- `nurunurun`
- `kukuros`
- `peka_pika`
- `shibazou`

正確な既定値や文字数制限は `GET /api/v1/templates` のレスポンスを参照してください。

## エラー仕様

入力不備、未知のテンプレート、文字数超過、画像パス不正などはHTTP 400でJSONを返します。

```json
{
  "ok": false,
  "error": "1件目: `name` は 6 文字以内にしてください。現在は 9 文字です。"
}
```

代表例:

| 状況 | HTTP | 内容 |
|---|---:|---|
| JSONボディなし | 400 | `JSONボディを送信してください。` |
| 未知のテンプレート | 400 | 利用可能なテンプレートID一覧を含むエラー |
| 文字数超過 | 400 | 対象フィールド、上限、現在文字数を返す |
| フォントサイズ範囲外 | 400 | 20から128の範囲で指定するよう返す |
| 画像が見つからない | 400 | 見つからない画像パスを返す |

## クライアント実装メモ

- PDFレスポンスはバイナリなので、ブラウザやHTTPクライアントではBlob/ファイルとして扱ってください。
- 空欄を送ると空文字として扱われる場合があります。テンプレート既定値を使いたい場合は、そのフィールド自体を送らない実装にしてください。
- フォントサイズを指定しない場合は、テンプレートJSONの既定サイズが使われます。
- テンプレート定義は `templates.json` で管理されています。
