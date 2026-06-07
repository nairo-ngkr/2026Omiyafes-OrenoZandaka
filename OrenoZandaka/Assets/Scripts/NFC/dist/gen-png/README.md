# FigmaカードPDF生成

Figmaで作成したカードデザインをテンプレート化し、JSON・Webフォーム・APIから文字を差し替えてPDFを生成するツールです。Docker Composeで `localhost:8080` に起動できます。

## できること

- 1051x1500px / 300DPI のカードPDF生成
- 8種類のカードテンプレート選択
- 単一カードPDF、複数ページPDFの生成
- `name` / `attribute` / `skill` / `phrase` / `habitat` / `description` / `hp` の差し替え
- `skill` / `phrase` / `habitat` のフォントサイズ個別指定
- 背景画像・キャラ画像の任意差し替え
- Webフォームと `/api/v1/` APIからのPDF生成

## 起動

```bash
cd /Users/nono/Documents/GitHub/print-unity-ofes2026/gen-print/gen-png
docker compose build
docker compose up
```

ブラウザで開く:

- http://localhost:8080
- http://localhost:8080/api/v1/

## CLIで生成

```bash
docker compose run --rm card-pdf --input /work/examples/card.json --output /work/output/card.pdf
```

8テンプレート混在の複数ページPDF:

```bash
docker compose run --rm card-pdf --input /work/examples/cards.json --output /work/output/templates-8.pdf --preview-dir /work/output/templates-8-preview
```

## API例

```bash
curl http://localhost:8080/api/v1/templates
```

```bash
curl -X POST http://localhost:8080/api/v1/generate \
  -H "Content-Type: application/json" \
  -d @examples/card.json \
  --output output/card.pdf
```

## ドキュメント

詳細は [docs/README.md](docs/README.md) を参照してください。

- [docs/API.md](docs/API.md): API仕様、リクエスト/レスポンス例、エラー仕様
- [docs/TEMPLATES.md](docs/TEMPLATES.md): テンプレート仕様
- [docs/ASSETS.md](docs/ASSETS.md): アセット管理

## テンプレートの既定値

`ぞくせい` / `とくぎ` / `くちぐせ` / `せいそくち` はテンプレートごとにFigma上の現在値を既定値として持ちます。入力しなかった項目は、そのテンプレートの既定値で出力されます。
## テンプレートJSON管理

テンプレート定義は `templates.json` で管理します。色、画像パス、座標、既定文字、文字数制限、フォントサイズを変更したい場合はこのJSONを編集してください。
