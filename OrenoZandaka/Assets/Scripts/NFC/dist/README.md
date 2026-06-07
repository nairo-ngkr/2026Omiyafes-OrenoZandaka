# Local NFC Print Runner

この `dist` フォルダは、zip にして別 PC へ持っていくための配布用フォルダです。展開後、仮想環境へ `pip install -r requirements.txt` して、次の 1 ファイルを実行するだけでローカル印刷フローを起動できます。

```powershell
py local_print.py
```

起動すると次の処理をまとめて行います。

- NFC を読み取る
- 残高からカードテンプレートを選ぶ
- `gen-png` で PDF と確認用 PNG を生成する
- Canon TS200 へ印刷ジョブを送る
- Unity の TCP listener へ JSON イベントを送る
- 手動テスト用 HTTP API を `0.0.0.0:8080` で待ち受ける

## フォルダ配置

zip 配布時は、この `dist` フォルダを丸ごと圧縮してください。展開先では次の配置になっていれば動きます。

```text
dist/
  local_print.py
  README.md
  requirements.txt
  run_local_print.py
  print_service.py
  print_ts200_l_size.py
  gen-png/
  nfc_reader/
  SumatraPDF-3.6-64/
  unity/
    UnityTcpPrintListener.cs
```

`gen-png/` と `nfc_reader/` は同梱済みです。`SumatraPDF-3.6-64/` は印刷時に外部 exe として呼び出すため、配布先で `SumatraPDF-3.6-64.exe` が入っているか確認してください。

## 初回セットアップ

Windows の PowerShell で実行します。

```powershell
cd path\to\dist
py -m venv .venv
.\.venv\Scripts\activate
py -m pip install -r requirements.txt
```

Unity 側には `unity\UnityTcpPrintListener.cs` を入れて、待ち受けポートを `9000` にしてください。

## 本番起動

```powershell
cd path\to\dist
.\.venv\Scripts\activate
py local_print.py --unity-host 127.0.0.1 --unity-port 9000
```

Unity が別 PC の場合は、`--unity-host` に Unity PC の LAN IP を指定します。

```powershell
py local_print.py --unity-host 192.168.1.50 --unity-port 9000
```

## 印刷なしテスト

NFC なし、印刷なしで HTTP API だけ起動します。

```powershell
py local_print.py --no-nfc --prepare-only --no-unity
```

別ターミナルから手動で印刷フローをテストできます。

```powershell
curl -X POST http://localhost:8080/print ^
  -H "Content-Type: application/json" ^
  -d "{\"uid\":\"TEST_UID\",\"balance\":400}"
```

## 出力先

```text
dist/output/unity_pdf/   生成PDF
dist/output/unity_png/   確認用PNG
dist/output/log/         JSON Linesログ
```

## よく使うオプション

```powershell
# プリンターへ送らず、PDF/PNG生成まで
py local_print.py --prepare-only

# NFCを使わず、HTTP APIだけ起動
py local_print.py --no-nfc

# Unityへ送らず、標準出力だけで確認
py local_print.py --no-unity

# LAN内のUnityへ送る
py local_print.py --unity-host 192.168.1.50 --unity-port 9000
```

## 注意

- 実印刷は Windows + SumatraPDF + Canon TS200 前提です。
- `localhost:8080` は手動テスト用 HTTP API が使います。既存の Docker `gen-png` API と同時に同じポートでは起動できません。
- `SumatraPDF-3.6-64/` は外部 exe として呼び出すため、`dist` 配下に置いてください。
- zip 化するときは `dist` フォルダの中身全体を含めてください。`local_print.py` だけでは動きません。
