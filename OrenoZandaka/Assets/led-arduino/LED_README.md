# LED Controller README

## 概要

Unity から Arduino Uno R3 にシリアル通信でコマンドを送り、LED 演出を切り替えるためのコードです。

Unity 側は `LedController.cs` を使います。Arduino 側は `aruduino_uno_r3/aruduino_uno_r3.ino` を Arduino Uno R3 に書き込んでください。

## Unity 側の使い方

1. 空の GameObject を作成する。
2. `LedController` を Add Component する。
3. `Led Serial Port Name` を Arduino の COM ポートに合わせる。
4. Play Mode に入る。
5. 他のスクリプトや UI Button から `LedController` の関数を呼ぶ。

例:

```csharp
public LedController ledController;

void Start()
{
    ledController.PlayLedWaitCardEffect();
}
```

## テスト用キー操作

`LedControllerTestInput` を同じ GameObject に Add Component すると、`L` キーで演出を順番に切り替えられます。

順番:

1. `Idle`
2. `WaitCard`
3. `Reading`
4. `Success`
5. `Error`

`L` を押すたびに Console に現在の演出が表示されます。

```text
LED test effect: Idle
LED test effect: WaitCard
LED test effect: Reading
LED test effect: Success
LED test effect: Error
```

## LED 演出一覧

### Idle

呼び出し:

```csharp
ledController.PlayLedIdleEffect();
```

送信コマンド:

```text
STATE:IDLE
```

光り方:

青と紫のゆっくりした呼吸発光です。通常待機中の状態に使います。

### WaitCard

呼び出し:

```csharp
ledController.PlayLedWaitCardEffect();
```

送信コマンド:

```text
STATE:WAIT_CARD
```

光り方:

3点の三角形スキャンです。ICカードをかざしてほしい場面に使います。

### Reading

呼び出し:

```csharp
ledController.PlayLedReadingEffect();
```

送信コマンド:

```text
STATE:READING
```

光り方:

9セクターを順番に点灯します。カード読み取り中や認証中に使います。

### Success

呼び出し:

```csharp
ledController.PlayLedSuccessEffect();
```

送信コマンド:

```text
STATE:SUCCESS
```

光り方:

白からシアンのフラッシュと高速回転演出です。成功後、自動で `Idle` に戻ります。

### Error

呼び出し:

```csharp
ledController.PlayLedErrorEffect();
```

送信コマンド:

```text
STATE:ERROR
```

光り方:

赤系の点滅と崩れるようなランダム発光です。Unity から次の状態が送られるまで `Error` 演出をループします。

## 汎用関数

演出を enum で指定する場合:

```csharp
ledController.PlayLedEffect(LedEffect.Success);
```

明るさ変更:

```csharp
ledController.SetLedBrightness(120);
```

範囲は `0` から `255` です。

色変更:

```csharp
ledController.SetLedColor(LedColor.Cyan);
```

対応色:

- `Blue`
- `Purple`
- `Cyan`
- `White`
- `Red`
- `Orange`
- `Gold`

通信確認:

```csharp
ledController.PingLedController();
```

Arduino には `PING` が送られます。

消灯:

```csharp
ledController.TurnOffLed();
```

Arduino には `STATE:OFF` が送られ、LED は消灯状態を維持します。`LedController` は通常終了時に自動で消灯してからシリアルポートを閉じます。

## 注意点

- Arduino IDE の Serial Monitor を開いたままだと Unity から同じ COM ポートに接続できません。
- Unity の `Api Compatibility Level` は `.NET Framework` にしてください。
- `Led Serial Port Name` は環境ごとに変わります。Windows では `COM3`, `COM4` などになります。
- 現在の Arduino 側演出は LED 27 個を前提にしています。LED 数を変える場合は `.ino` 側の演出計算も調整が必要です。
