#include <Adafruit_NeoPixel.h>

#define LED_PIN 6
#define LED_COUNT 27
#define DEFAULT_BRIGHTNESS 100
#define SERIAL_BAUD 115200

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

enum LedState {
  STATE_IDLE,
  STATE_WAIT_CARD,
  STATE_READING,
  STATE_SUCCESS,
  STATE_ERROR,
  STATE_OFF
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
  } else if (cmd == "STATE:OFF") {
    setState(STATE_OFF);
    Serial.println("OK:STATE:OFF");
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
    case STATE_OFF:
      animateOff();
      break;
  }
}

void animateOff() {
  // Keep LEDs off until Unity sends the next state.
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
    errorFrame = 0;
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
