/*
  Arduino Uno R3 + WS2812B / NeoPixel 27 LEDs
  Magic Circle LED Controller for Unity Serial Control

  Hardware assumption:
  - Board: Arduino Uno R3
  - LED: WS2812B / NeoPixel / SK6812 compatible addressable LEDs
  - LED count: 27
  - LED data pin: D6
  - External LED power: 5V 2A or higher recommended
  - Arduino GND and LED power supply GND must be common

  Unity sends line-based Serial commands:
    STATE:IDLE
    STATE:WAIT_CARD
    STATE:READING
    STATE:SUCCESS
    STATE:ERROR
    BRIGHTNESS:120
    COLOR:CYAN

  Required Arduino Library:
  - Adafruit NeoPixel

  Recommended Arduino IDE settings:
  - Board: Arduino Uno
  - Processor: ATmega328P
  - Baud rate in Serial Monitor / Unity: 115200
*/

#include <Adafruit_NeoPixel.h>

#define LED_PIN 6
#define LED_COUNT 27
#define DEFAULT_BRIGHTNESS 80
#define SERIAL_BAUD 115200

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

enum LedState {
  STATE_IDLE,
  STATE_WAIT_CARD,
  STATE_READING,
  STATE_SUCCESS,
  STATE_ERROR
};

LedState currentState = STATE_IDLE;
LedState previousState = STATE_IDLE;

uint8_t globalBrightness = DEFAULT_BRIGHTNESS;
uint32_t baseColor;

unsigned long stateStartMs = 0;
unsigned long lastFrameMs = 0;

int waitFrame = 0;
int readingSector = 0;
int successFrame = 0;
int errorFrame = 0;

String serialBuffer = "";

uint32_t colorBlue;
uint32_t colorPurple;
uint32_t colorCyan;
uint32_t colorWhite;
uint32_t colorRed;
uint32_t colorOrange;
uint32_t colorGold;

void setup() {
  Serial.begin(SERIAL_BAUD);

  strip.begin();
  strip.setBrightness(globalBrightness);
  strip.show();

  colorBlue   = strip.Color(0, 40, 255);
  colorPurple = strip.Color(120, 0, 255);
  colorCyan   = strip.Color(0, 180, 255);
  colorWhite  = strip.Color(255, 255, 255);
  colorRed    = strip.Color(255, 0, 0);
  colorOrange = strip.Color(255, 80, 0);
  colorGold   = strip.Color(255, 170, 40);

  baseColor = colorCyan;
  setState(STATE_IDLE);

  Serial.println("READY:MAGIC_CIRCLE_LED_CONTROLLER");
}

void loop() {
  readSerialCommands();
  updateAnimation();
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        handleCommand(serialBuffer);
        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
      if (serialBuffer.length() > 64) {
        serialBuffer = "";
      }
    }
  }
}

void handleCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "STATE:IDLE") {
    setState(STATE_IDLE);
    Serial.println("OK:STATE:IDLE");
  } else if (cmd == "STATE:WAIT_CARD") {
    setState(STATE_WAIT_CARD);
    Serial.println("OK:STATE:WAIT_CARD");
  } else if (cmd == "STATE:READING") {
    setState(STATE_READING);
    Serial.println("OK:STATE:READING");
  } else if (cmd == "STATE:SUCCESS") {
    setState(STATE_SUCCESS);
    Serial.println("OK:STATE:SUCCESS");
  } else if (cmd == "STATE:ERROR") {
    setState(STATE_ERROR);
    Serial.println("OK:STATE:ERROR");
  } else if (cmd.startsWith("BRIGHTNESS:")) {
    int value = cmd.substring(11).toInt();
    value = constrain(value, 0, 255);
    globalBrightness = (uint8_t)value;
    strip.setBrightness(globalBrightness);
    strip.show();
    Serial.print("OK:BRIGHTNESS:");
    Serial.println(globalBrightness);
  } else if (cmd.startsWith("COLOR:")) {
    setBaseColorFromCommand(cmd.substring(6));
    Serial.println("OK:COLOR");
  } else if (cmd == "PING") {
    Serial.println("PONG");
  } else {
    Serial.print("ERR:UNKNOWN_COMMAND:");
    Serial.println(cmd);
  }
}

void setBaseColorFromCommand(String colorName) {
  colorName.trim();
  colorName.toUpperCase();

  if (colorName == "BLUE") {
    baseColor = colorBlue;
  } else if (colorName == "PURPLE") {
    baseColor = colorPurple;
  } else if (colorName == "CYAN") {
    baseColor = colorCyan;
  } else if (colorName == "WHITE") {
    baseColor = colorWhite;
  } else if (colorName == "RED") {
    baseColor = colorRed;
  } else if (colorName == "ORANGE") {
    baseColor = colorOrange;
  } else if (colorName == "GOLD") {
    baseColor = colorGold;
  }
}

void setState(LedState nextState) {
  previousState = currentState;
  currentState = nextState;
  stateStartMs = millis();
  lastFrameMs = 0;

  waitFrame = 0;
  readingSector = 0;
  successFrame = 0;
  errorFrame = 0;

  clearLeds();
}

void updateAnimation() {
  switch (currentState) {
    case STATE_IDLE:
      animateIdle();
      break;
    case STATE_WAIT_CARD:
      animateWaitCard();
      break;
    case STATE_READING:
      animateReading();
      break;
    case STATE_SUCCESS:
      animateSuccess();
      break;
    case STATE_ERROR:
      animateError();
      break;
  }
}

void animateIdle() {
  unsigned long now = millis();
  if (now - lastFrameMs < 25) return;
  lastFrameMs = now;

  float phase = (now % 3000) / 3000.0;
  float wave = (sin(phase * 2.0 * PI) + 1.0) * 0.5;
  uint8_t level = 10 + (uint8_t)(wave * 35);

  uint32_t c = scaleColor(mixColor(colorBlue, colorPurple, 0.45), level);
  fillAll(c);
  strip.show();
}

void animateWaitCard() {
  unsigned long now = millis();
  if (now - lastFrameMs < 85) return;
  lastFrameMs = now;

  fadeAll(28);

  // 120-degree triangle scan: LED n, n+9, n+18
  int a = waitFrame % 9;
  int b = a + 9;
  int c = a + 18;

  strip.setPixelColor(a, scaleColor(baseColor, 180));
  strip.setPixelColor(b, scaleColor(baseColor, 180));
  strip.setPixelColor(c, scaleColor(baseColor, 180));

  // Every 9 frames, apply a light full-circle pulse to guide attention to the center.
  if (waitFrame % 9 == 0) {
    for (int i = 0; i < LED_COUNT; i++) {
      if (i % 3 == 0) {
        strip.setPixelColor(i, scaleColor(colorWhite, 60));
      }
    }
  }

  strip.show();
  waitFrame++;
}

void animateReading() {
  unsigned long now = millis();
  unsigned long elapsed = now - stateStartMs;

  int interval = 140;
  if (elapsed > 1500) interval = 105;
  if (elapsed > 3000) interval = 70;

  if (now - lastFrameMs < interval) return;
  lastFrameMs = now;

  fadeAll(45);

  // 9 sectors, each sector has 3 LEDs.
  int startLed = readingSector * 3;
  for (int i = 0; i < 3; i++) {
    strip.setPixelColor(startLed + i, scaleColor(baseColor, 210));
  }

  // Soft residual glow for already scanned sectors.
  for (int s = 0; s < 9; s++) {
    if (s != readingSector) {
      int led = s * 3 + 1;
      strip.setPixelColor(led, addColor(strip.getPixelColor(led), scaleColor(colorCyan, 18)));
    }
  }

  strip.show();
  readingSector = (readingSector + 1) % 9;
}

void animateSuccess() {
  unsigned long now = millis();
  if (now - lastFrameMs < 45) return;
  lastFrameMs = now;

  if (successFrame == 0) {
    clearLeds();
  } else if (successFrame == 1 || successFrame == 3) {
    fillAll(colorWhite);
  } else if (successFrame == 2) {
    clearLeds();
  } else if (successFrame < 22) {
    fadeAll(36);
    int head = successFrame % LED_COUNT;
    int tail1 = (head - 1 + LED_COUNT) % LED_COUNT;
    int tail2 = (head - 2 + LED_COUNT) % LED_COUNT;
    strip.setPixelColor(head, colorWhite);
    strip.setPixelColor(tail1, scaleColor(colorCyan, 180));
    strip.setPixelColor(tail2, scaleColor(colorCyan, 90));
  } else if (successFrame < 42) {
    uint8_t level = map(successFrame, 22, 41, 170, 15);
    fillAll(scaleColor(colorCyan, level));
  } else {
    setState(STATE_IDLE);
    return;
  }

  strip.show();
  successFrame++;
}

void animateError() {
  unsigned long now = millis();
  if (now - lastFrameMs < 70) return;
  lastFrameMs = now;

  if (errorFrame < 6) {
    if (errorFrame % 2 == 0) {
      fillAll(scaleColor(colorRed, 180));
    } else {
      clearLeds();
    }
  } else if (errorFrame < 26) {
    fadeAll(70);
    int p1 = random(LED_COUNT);
    int p2 = random(LED_COUNT);
    strip.setPixelColor(p1, scaleColor(colorRed, random(80, 220)));
    strip.setPixelColor(p2, scaleColor(colorOrange, random(30, 120)));
  } else if (errorFrame < 44) {
    uint8_t level = map(errorFrame, 26, 43, 80, 0);
    fillAll(scaleColor(colorRed, level));
  } else {
    setState(STATE_WAIT_CARD);
    return;
  }

  strip.show();
  errorFrame++;
}

void clearLeds() {
  for (int i = 0; i < LED_COUNT; i++) {
    strip.setPixelColor(i, 0);
  }
  strip.show();
}

void fillAll(uint32_t c) {
  for (int i = 0; i < LED_COUNT; i++) {
    strip.setPixelColor(i, c);
  }
}

void fadeAll(uint8_t amount) {
  for (int i = 0; i < LED_COUNT; i++) {
    uint32_t c = strip.getPixelColor(i);
    uint8_t r = (uint8_t)(c >> 16);
    uint8_t g = (uint8_t)(c >> 8);
    uint8_t b = (uint8_t)c;

    r = (r > amount) ? r - amount : 0;
    g = (g > amount) ? g - amount : 0;
    b = (b > amount) ? b - amount : 0;

    strip.setPixelColor(i, strip.Color(r, g, b));
  }
}

uint32_t scaleColor(uint32_t c, uint8_t scale) {
  uint8_t r = (uint8_t)(c >> 16);
  uint8_t g = (uint8_t)(c >> 8);
  uint8_t b = (uint8_t)c;

  r = ((uint16_t)r * scale) / 255;
  g = ((uint16_t)g * scale) / 255;
  b = ((uint16_t)b * scale) / 255;

  return strip.Color(r, g, b);
}

uint32_t addColor(uint32_t a, uint32_t b) {
  uint8_t ar = (uint8_t)(a >> 16);
  uint8_t ag = (uint8_t)(a >> 8);
  uint8_t ab = (uint8_t)a;

  uint8_t br = (uint8_t)(b >> 16);
  uint8_t bg = (uint8_t)(b >> 8);
  uint8_t bb = (uint8_t)b;

  uint8_t r = min(255, ar + br);
  uint8_t g = min(255, ag + bg);
  uint8_t bl = min(255, ab + bb);

  return strip.Color(r, g, bl);
}

uint32_t mixColor(uint32_t a, uint32_t b, float t) {
  t = constrain(t, 0.0, 1.0);

  uint8_t ar = (uint8_t)(a >> 16);
  uint8_t ag = (uint8_t)(a >> 8);
  uint8_t ab = (uint8_t)a;

  uint8_t br = (uint8_t)(b >> 16);
  uint8_t bg = (uint8_t)(b >> 8);
  uint8_t bb = (uint8_t)b;

  uint8_t r = ar + (br - ar) * t;
  uint8_t g = ag + (bg - ag) * t;
  uint8_t bl = ab + (bb - ab) * t;

  return strip.Color(r, g, bl);
}

/*
================================================================================
Unityからの操作マニュアル・設定方法
================================================================================

1. Arduino IDE側の準備
--------------------------------------------------------------------------------
1) Arduino IDEを起動する。
2) Library Managerで「Adafruit NeoPixel」をインストールする。
3) Arduino Uno R3をUSB接続する。
4) Tools > Board で「Arduino Uno」を選択する。
5) Tools > Port でArduino UnoのCOMポートを選択する。
6) このスケッチを書き込む。
7) Serial Monitorを開き、baud rateを115200にする。
8) 起動時に以下が表示されればArduino側は動作している。

   READY:MAGIC_CIRCLE_LED_CONTROLLER

2. 配線
--------------------------------------------------------------------------------
WS2812B / NeoPixel 27個を使う前提。

Arduino Uno R3:
  D6  -> LED DIN
  GND -> LED電源GNDと共通化

外部5V電源:
  5V  -> LED 5V
  GND -> LED GND

重要:
- LED 27個をArduinoの5Vピンから直接給電しない。
- 27個 x 最大約60mA = 最大約1.62Aを想定する。
- 5V 2A以上、余裕を見るなら5V 3Aの外部電源を使う。
- Arduino GNDとLED電源GNDは必ず接続する。
- LED DINの手前に330Ω程度の抵抗を入れると信号保護になる。
- LED電源の5V-GND間に1000µF程度の電解コンデンサを入れると安定しやすい。

3. Unity側 Project Settings
--------------------------------------------------------------------------------
UnityでSerialPortを使うには、環境によってApi Compatibility Levelの変更が必要。

Unity Editor:
  Edit > Project Settings > Player > Other Settings

推奨:
  Api Compatibility Level: .NET Framework

古いUnityでは以下の場合がある。
  Api Compatibility Level: .NET 4.x

4. Unity C# サンプルコード
--------------------------------------------------------------------------------
以下のスクリプトを MagicCircleLedSerial.cs として作成し、空のGameObjectに追加する。
COMポート名は環境に合わせて変更する。

Windows例:
  COM3
  COM4

macOS例:
  /dev/tty.usbmodemXXXX

using UnityEngine;
using System;
using System.IO.Ports;

public class MagicCircleLedSerial : MonoBehaviour
{
    [Header("Serial Settings")]
    public string portName = "COM3";
    public int baudRate = 115200;

    private SerialPort serialPort;

    void Start()
    {
        OpenPort();
    }

    void OnDestroy()
    {
        ClosePort();
    }

    void OnApplicationQuit()
    {
        ClosePort();
    }

    public void OpenPort()
    {
        try
        {
            if (serialPort != null && serialPort.IsOpen) return;

            serialPort = new SerialPort(portName, baudRate);
            serialPort.NewLine = "\n";
            serialPort.ReadTimeout = 50;
            serialPort.WriteTimeout = 50;
            serialPort.Open();

            Debug.Log("Arduino serial connected: " + portName);
        }
        catch (Exception e)
        {
            Debug.LogError("Failed to open serial port: " + e.Message);
        }
    }

    public void ClosePort()
    {
        try
        {
            if (serialPort != null && serialPort.IsOpen)
            {
                serialPort.Close();
                Debug.Log("Arduino serial closed");
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning("Failed to close serial port: " + e.Message);
        }
    }

    public void SendCommand(string command)
    {
        if (serialPort == null || !serialPort.IsOpen)
        {
            Debug.LogWarning("Serial port is not open");
            return;
        }

        try
        {
            serialPort.WriteLine(command);
            Debug.Log("Send to Arduino: " + command);
        }
        catch (Exception e)
        {
            Debug.LogError("Serial write failed: " + e.Message);
        }
    }

    public void SetIdle()
    {
        SendCommand("STATE:IDLE");
    }

    public void SetWaitCard()
    {
        SendCommand("STATE:WAIT_CARD");
    }

    public void SetReading()
    {
        SendCommand("STATE:READING");
    }

    public void SetSuccess()
    {
        SendCommand("STATE:SUCCESS");
    }

    public void SetError()
    {
        SendCommand("STATE:ERROR");
    }

    public void SetBrightness(int brightness)
    {
        brightness = Mathf.Clamp(brightness, 0, 255);
        SendCommand("BRIGHTNESS:" + brightness);
    }

    public void SetColorCyan()
    {
        SendCommand("COLOR:CYAN");
    }

    public void SetColorBlue()
    {
        SendCommand("COLOR:BLUE");
    }

    public void SetColorPurple()
    {
        SendCommand("COLOR:PURPLE");
    }

    public void Ping()
    {
        SendCommand("PING");
    }
}

5. Unityからの基本操作
--------------------------------------------------------------------------------
ゲーム状態に合わせて以下を呼ぶ。

ゲーム開始:
  magicCircleLedSerial.SetIdle();

ICカードを要求する画面:
  magicCircleLedSerial.SetWaitCard();

カード検出後、読み取り開始:
  magicCircleLedSerial.SetReading();

認証成功:
  magicCircleLedSerial.SetSuccess();

認証失敗:
  magicCircleLedSerial.SetError();

明るさ変更:
  magicCircleLedSerial.SetBrightness(120);

色変更:
  magicCircleLedSerial.SendCommand("COLOR:CYAN");

6. Unity UI Buttonから操作する方法
--------------------------------------------------------------------------------
1) Hierarchyで空のGameObjectを作成する。
2) 名前を MagicCircleLedController にする。
3) MagicCircleLedSerial.cs をAdd Componentする。
4) portNameをArduinoのCOMポートに合わせる。
5) ButtonのOnClickに MagicCircleLedController を割り当てる。
6) 呼びたい関数を選ぶ。

例:
  Button: 待機
    OnClick -> MagicCircleLedSerial.SetIdle

  Button: カード待ち
    OnClick -> MagicCircleLedSerial.SetWaitCard

  Button: 読み取り中
    OnClick -> MagicCircleLedSerial.SetReading

  Button: 成功
    OnClick -> MagicCircleLedSerial.SetSuccess

  Button: 失敗
    OnClick -> MagicCircleLedSerial.SetError

7. ICカード読み取り処理との連携例
--------------------------------------------------------------------------------
疑似コード:

void OnGameStart()
{
    led.SetIdle();
}

void OnNeedCard()
{
    led.SetWaitCard();
    // Unity画面: 「カードを魔法陣にかざしてください」
    // SE: 低い魔力音
}

void OnCardDetected()
{
    led.SetReading();
    // Unity画面: 「認証中」
}

void OnCardReadSuccess()
{
    led.SetSuccess();
    // Unity画面: 「魔法発動」
    // SE: 成功音
}

void OnCardReadFailed()
{
    led.SetError();
    // Unity画面: 「読み取り失敗」
    // SE: 失敗音
}

8. コマンド仕様
--------------------------------------------------------------------------------
Unity -> Arduino:

STATE:IDLE
  待機。青紫の呼吸発光。

STATE:WAIT_CARD
  ICカード待ち。3点三角形スキャン。

STATE:READING
  読み取り中。9セクター順次点火。

STATE:SUCCESS
  成功。白〜シアンのフラッシュと高速回転後、自動でIDLEへ戻る。

STATE:ERROR
  失敗。赤系点滅と崩壊演出後、自動でWAIT_CARDへ戻る。

BRIGHTNESS:0〜255
  LED全体の明るさを変更。
  推奨値:
    通常: 20〜80
    演出: 100〜160
    強フラッシュ: 180〜200程度

COLOR:BLUE
COLOR:PURPLE
COLOR:CYAN
COLOR:WHITE
COLOR:RED
COLOR:ORANGE
COLOR:GOLD
  WAIT_CARD / READING系の基本色を変更。

PING
  通信確認。ArduinoからPONGが返る。

9. 動作確認手順
--------------------------------------------------------------------------------
1) Arduinoにスケッチを書き込む。
2) Arduino IDEのSerial Monitorを開く。
3) baud rateを115200にする。
4) 以下を1行ずつ送る。

STATE:IDLE
STATE:WAIT_CARD
STATE:READING
STATE:SUCCESS
STATE:ERROR
BRIGHTNESS:40
BRIGHTNESS:120
COLOR:CYAN
PING

5) Arduino IDEのSerial Monitorを閉じる。
   UnityとArduino IDEが同じCOMポートを同時に使うことはできない。
6) Unityを起動し、同じCOMポートを設定する。
7) Unityから各状態メソッドを呼び、LED演出を確認する。

10. よくある問題
--------------------------------------------------------------------------------
問題: Unityから接続できない
原因:
- Arduino IDEのSerial Monitorが開いたまま
- COMポート名が違う
- baud rateがArduino側と違う

対処:
- Serial Monitorを閉じる
- WindowsのデバイスマネージャーでCOM番号を確認
- Unity側のbaudRateを115200にする

問題: LEDが光らない
原因:
- LEDのDIN方向が逆
- GND共通化ができていない
- 外部5V電源が入っていない
- LED_PINが違う

対処:
- LEDテープの矢印方向を確認
- Arduino GNDとLED電源GNDを接続
- LED DINがArduino D6に入っているか確認

問題: 色がおかしい
原因:
- LEDの色順がGRBではない

対処:
- Adafruit_NeoPixelの初期化を変更する。

現在:
  Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

試す候補:
  NEO_RGB + NEO_KHZ800
  NEO_GRBW + NEO_KHZ800

問題: 成功演出のフラッシュが眩しすぎる
対処:
- Unityから BRIGHTNESS:80 などを送る。
- DEFAULT_BRIGHTNESSを下げる。
- animateSuccess内のcolorWhiteやscale値を下げる。

11. 推奨運用
--------------------------------------------------------------------------------
- Unity側はLEDを1個ずつ直接制御しない。
- Unityはゲーム状態だけをArduinoへ送る。
- Arduino側に演出ロジックを持たせる。
- WAIT_CARDでは画面表示、効果音、LED演出を同期する。
- SUCCESS / ERRORは自動復帰するため、必要に応じてUnityから次状態を再送する。
*/
