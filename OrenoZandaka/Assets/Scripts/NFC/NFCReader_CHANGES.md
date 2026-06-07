# NFCReader.cs 変更ログ

## 変更概要

- **モバイルSuica対応**: 残高読み取りサービスを `0x090F`（履歴）から `0x008B`（残高直読み）に変更し、物理・モバイル共通で動作するよう安定化
- **NTAG215デモカード対応**: NDEFテキストを読み取って識別し、デモ用UID/残高を `GetNtagDemoValues()` で返す仕組みを追加

---

## 追加機能

| 機能 | メソッド | 概要 |
|------|---------|------|
| UID読み取りの独立化 | `ReadUID()` | 既存ロジックをヘルパーへ分離 |
| NDEFテキスト読み取り | `TryReadNdefText()` | NTAG215のページ4からNDEFを解析 |
| NDEFパース | `ParseNdefTextRecord()` | Well-Known Text レコードを文字列化 |
| デモ値プレースホルダー | `GetNtagDemoValues()` | TODO箇所にデモロジックを実装する |
| 残高読み取り独立化 | `TryReadBalance()` | サービス0x008Bで物理・モバイルSuica共通読み取り |

---

## 変更前後の比較

### ProcessCardData() — コア処理

**変更前**
```csharp
private void ProcessCardData()
{
    if (context == null || !context.IsValid()) return;
    try
    {
        using (var reader = context.ConnectReader(...))
        {
            byte[] receiveBuffer = new byte[256];

            // UUID取得
            var apdu = new CommandApdu(...) { ... };
            int received = reader.Transmit(..., apdu.ToArray(), receiveBuffer);
            var res = new ResponseApdu(receiveBuffer, received, ...);
            if (res.SW1 == 0x90)
            {
                string uid = BitConverter.ToString(res.GetData());
                mainThreadContext.Post(_ => ActionOnReadCard?.Invoke(uid), null);
            }

            // 残高取得 (サービス 0x090F)
            byte[] selectFile = { 0xff, 0xA4, 0x00, 0x01, 0x02, 0x0f, 0x09 };
            reader.Transmit(..., selectFile, receiveBuffer);
            byte[] readBinary = { 0xff, 0xb0, 0x00, 0x00, 0x00 };
            received = reader.Transmit(..., readBinary, receiveBuffer);
            var resBal = new ResponseApdu(receiveBuffer, received, ...);
            if (resBal.SW1 == 0x90 && resBal.HasData)
            {
                byte[] data = resBal.GetData();
                if (data.Length >= 12)
                {
                    int balance = BitConverter.ToInt16(new byte[] { data[10], data[11] }, 0);
                    mainThreadContext.Post(_ => ActionOnReadTransportationICCard?.Invoke(balance), null);
                }
            }
        }
    }
    catch (Exception e)
    {
        Debug.Log($"Card Process Error: {e.Message}");
        isProcessing = false;
    }
}
```

**変更後**
```csharp
private void ProcessCardData()
{
    if (context == null || !context.IsValid()) return;
    try
    {
        using (var reader = context.ConnectReader(...))
        {
            byte[] buf = new byte[256];
            string rawUID = ReadUID(reader, buf);
            if (rawUID == null) return;

            string ndefText = TryReadNdefText(reader, buf);

            if (ndefText != null)
            {
                // NTAG215 分岐
                var (uid, balance) = GetNtagDemoValues(ndefText);
                mainThreadContext.Post(_ => ActionOnReadCard?.Invoke(uid), null);
                if (balance >= 0)
                {
                    int captured = balance;
                    mainThreadContext.Post(_ => ActionOnReadTransportationICCard?.Invoke(captured), null);
                }
            }
            else
            {
                // Suica / モバイルSuica 分岐
                mainThreadContext.Post(_ => ActionOnReadCard?.Invoke(rawUID), null);
                int balance = TryReadBalance(reader, buf);
                if (balance >= 0)
                {
                    int captured = balance;
                    mainThreadContext.Post(_ => ActionOnReadTransportationICCard?.Invoke(captured), null);
                }
            }
        }
    }
    catch (Exception e)
    {
        Debug.Log($"Card Process Error: {e.Message}");
        isProcessing = false;
    }
}
```

### 残高サービスコード変更

| | 変更前 | 変更後 |
|--|--------|--------|
| サービスコード | `0x090F`（履歴サービス） | `0x008B`（残高直読み） |
| APDUバイト列 | `FF A4 00 01 02 0F 09` | `FF A4 00 01 02 8B 00` |
| 残高データ型 | `BitConverter.ToInt16`（符号あり） | `BitConverter.ToUInt16`（符号なし） |

---

## NTAG215 カード準備手順

1. **「NFC Tools」アプリ**（Android/iOS、無料）をスマートフォンにインストール
2. NTAG215シールをスマートフォンにかざす
3. Write → Add a record → Text を選択
4. 識別子テキストを入力（例: `DRAGON`、`FIRE`、`WATER` など半角英数字推奨）
5. Write で書き込む

書き込んだテキストが `GetNtagDemoValues()` の `ndefText` 引数に渡される。  
MonsterManagerへ報告されるUIDは `"NTAG215-DRAGON"` のような形式になる。

---

## GetNtagDemoValues() 実装ガイド

現在 `balance = -1`（残高イベント非発火）のプレースホルダーになっている。

```csharp
private (string uid, int balance) GetNtagDemoValues(string ndefText)
{
    string uid = "NTAG215-" + ndefText;

    // TODO: ここにランダム値などのデモロジックを実装
    int balance = -1;

    return (uid, balance);
}
```

### 実装例: ndefText に応じて固定の残高を返す

```csharp
int balance = ndefText switch
{
    "DRAGON" => 9999,
    "FIRE"   => 5000,
    "WATER"  => 1000,
    _        => UnityEngine.Random.Range(0, 9999),
};
```

### 実装例: 常にランダムな残高を返す

```csharp
int balance = UnityEngine.Random.Range(0, 9999);
```

> **注意**: `GetNtagDemoValues()` はバックグラウンドスレッドから呼ばれる。  
> `UnityEngine.Random` はメインスレッド以外でも呼び出し可能。  
> ただし MonoBehaviour のフィールドや Unity API（GameObject等）にはアクセスしないこと。
