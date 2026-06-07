# LED Control Spec for Unity AI

この文書は、Unity のコードを書く AI / 実装者が `led-arduino` の LED 制御を正しく扱うための仕様書です。

## 目的

Unity から Arduino Uno R3 にシリアル通信で短いテキストコマンドを送り、Arduino 側で定義済みの LED 演出を再生します。

Unity 側で LED 1 個ずつの点灯制御は行いません。Unity はゲーム状態に応じて「どの演出を再生するか」だけを Arduino に送ります。

## 対象ファイル

- Unity 側制御コード: `Assets/led-arduino/LedController.cs`
- Unity 側テスト入力: `Assets/led-arduino/LedControllerTestInput.cs`
- Arduino 側スケッチ: `Assets/led-arduino/aruduino_uno_r3/aruduino_uno_r3.ino`

## 通信仕様

Unity から Arduino へ、改行区切りのテキストコマンドを送ります。

- Baud rate: `115200`
- NewLine: `\n`
- Arduino 起動時ログ: `READY:MAGIC_CIRCLE_LED_CONTROLLER`
- Arduino 成功応答例: `OK:STATE:IDLE`
- Arduino エラー応答例: `ERR:UNKNOWN_COMMAND:...`

Unity 側コードでは、基本的に `LedController` の公開関数を呼び、直接コマンド文字列を組み立てないでください。

## Unity 側コンポーネント

空の GameObject に `LedController` を Add Component して使います。

Inspector 設定:

| Field | Default | Description |
| --- | --- | --- |
| `ledSerialPortName` | `COM3` | Arduino の COM ポート名。環境に合わせて `COM7` などに変更する。 |
| `ledSerialBaudRate` | `115200` | Arduino 側の `SERIAL_BAUD` と一致させる。 |
| `openLedSerialOnStart` | `true` | `Start()` で自動接続する。 |
| `turnOffLedOnQuit` | `true` | Unity 終了時に `STATE:OFF` を送って消灯する。 |
| `logLedCommands` | `true` | Console に接続・送信ログを出す。 |

Unity の `Project Settings > Player > Api Compatibility Level` は `.NET Framework` にしてください。

## Unity 公開 API

### 接続

```csharp
ledController.OpenLedSerialPort();
ledController.CloseLedSerialPort();
```

通常は `openLedSerialOnStart = true` のままでよく、手動接続は不要です。

### 任意コマンド送信

```csharp
ledController.SendLedCommand("STATE:IDLE");
```

原則として、通常のゲームコードでは直接使わず、下記の専用関数を使ってください。

### 演出再生

```csharp
ledController.PlayLedIdleEffect();
ledController.PlayLedWaitCardEffect();
ledController.PlayLedReadingEffect();
ledController.PlayLedSuccessEffect();
ledController.PlayLedErrorEffect();
```

enum で指定する場合:

```csharp
ledController.PlayLedEffect(LedEffect.WaitCard);
```

`LedEffect` の値:

```csharp
Idle
WaitCard
Reading
Success
Error
```

### 消灯

```csharp
ledController.TurnOffLed();
```

`STATE:OFF` を送ります。Unity を正しく終了した場合は、`turnOffLedOnQuit = true` により自動で呼ばれます。

### 明るさ

```csharp
ledController.SetLedBrightness(120);
```

値は `0` から `255` です。Unity 側で clamp されます。

推奨値:

- 暗め: `20`
- 通常: `40` から `80`
- 演出強め: `100` から `160`
- 強フラッシュ: `180` から `200`

### 色

```csharp
ledController.SetLedColor(LedColor.Cyan);
```

`LedColor` の値:

```csharp
Blue
Purple
Cyan
White
Red
Orange
Gold
```

色変更は主に `WAIT_CARD` / `READING` 系の基本色に影響します。`IDLE`, `SUCCESS`, `ERROR` は Arduino 側で演出色が固定寄りです。

### 通信確認

```csharp
ledController.PingLedController();
```

Arduino へ `PING` を送ります。Arduino は `PONG` を返しますが、現在の Unity 側コードは応答読み取りを必須機能として扱っていません。

## Arduino コマンド一覧

| Command | Unity API | Behavior |
| --- | --- | --- |
| `STATE:IDLE` | `PlayLedIdleEffect()` | 青紫の呼吸発光。待機状態。 |
| `STATE:WAIT_CARD` | `PlayLedWaitCardEffect()` | 3点三角形スキャン。カード待ち状態。 |
| `STATE:READING` | `PlayLedReadingEffect()` | 9セクター順次点灯。読み取り中状態。 |
| `STATE:SUCCESS` | `PlayLedSuccessEffect()` | 白からシアンのフラッシュと高速回転。完了後、自動で `IDLE` に戻る。 |
| `STATE:ERROR` | `PlayLedErrorEffect()` | 赤系点滅とランダム崩壊演出。次状態が来るまでループする。 |
| `STATE:OFF` | `TurnOffLed()` | 全LED消灯。次状態が来るまで消灯を維持する。 |
| `BRIGHTNESS:0-255` | `SetLedBrightness(value)` | 全体明るさを変更する。 |
| `COLOR:CYAN` など | `SetLedColor(color)` | 基本色を変更する。 |
| `PING` | `PingLedController()` | Arduino が `PONG` を返す。 |

## 推奨するゲーム状態との対応

| Game state | LED call |
| --- | --- |
| 起動直後 / 通常待機 | `PlayLedIdleEffect()` |
| カードを要求する画面 | `PlayLedWaitCardEffect()` |
| カード検出後、読み取り中 | `PlayLedReadingEffect()` |
| 認証成功 / 魔法発動 | `PlayLedSuccessEffect()` |
| 認証失敗 / エラー表示 | `PlayLedErrorEffect()` |
| ゲーム終了 / アプリ終了 | `TurnOffLed()` |

実装例:

```csharp
public class CardFlowLedPresenter : MonoBehaviour
{
    [SerializeField] private LedController ledController;

    public void OnNeedCard()
    {
        ledController.PlayLedWaitCardEffect();
    }

    public void OnCardDetected()
    {
        ledController.PlayLedReadingEffect();
    }

    public void OnCardReadSuccess()
    {
        ledController.PlayLedSuccessEffect();
    }

    public void OnCardReadFailed()
    {
        ledController.PlayLedErrorEffect();
    }
}
```

## テスト方法

`LedControllerTestInput` を `LedController` と同じ GameObject に Add Component します。

Play Mode 中に `L` キーを押すたびに、以下の順で演出が進みます。

```text
Idle -> WaitCard -> Reading -> Success -> Error -> Idle ...
```

Console には現在送った演出が出ます。

```text
LED test effect: WaitCard
Send to LED controller: STATE:WAIT_CARD
```

このプロジェクトは新 Input System 設定でも動くように、`LedControllerTestInput` は `Keyboard.current.lKey.wasPressedThisFrame` を使います。

## 実装上の注意

- Arduino IDE の Serial Monitor を開いたままだと、Unity は同じ COM ポートに接続できません。
- `LED serial connected: COM7` のようなログは接続成功です。
- `LED serial port is not open` が出る場合は、COM ポート名、Arduino 接続、Serial Monitor が閉じているかを確認してください。
- `System.IO.Ports.SerialPort is not available` が出る場合は、Unity の Api Compatibility Level を `.NET Framework` にしてください。
- 現在の Arduino 側演出は `LED_COUNT 27` を前提にした箇所があります。LED 数を変える場合、`WAIT_CARD` と `READING` の演出計算も調整してください。
- `SUCCESS` は Arduino 側で自動的に `IDLE` に戻ります。
- `ERROR` は自動復帰せず、Unity から別状態を送るまでループします。
- Unity 終了時の消灯は `OnDestroy()` / `OnApplicationQuit()` で `STATE:OFF` を送る設計です。強制終了やクラッシュ時は送れない場合があります。

