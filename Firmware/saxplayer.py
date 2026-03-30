include <Arduino.h>
include <Wire.h>
include <SPI.h>
include <SD.h>
include <Adafruit_GFX.h>
include <Adafruit_SSD1306.h>
include <AudioFileSourceSD.h>
include <AudioGeneratorMP3.h>
include <AudioOutputI2S.h>

define SCREEN_WIDTH 128
define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

AudioGeneratorMP3 *mp3 = nullptr;
AudioFileSourceSD *file = nullptr;
AudioOutputI2S *out = nullptr;

const int btn1 = 32;
const int btn2 = 33;
const int btn3 = 34;

const int encA = 13;
const int encB = 14;
const int encSW = 27;

volatile int encoderPos = 0;
int lastA = 0;

File root;
String files[100];
int fileCount = 0;
int currentTrack = 0;
bool playing = false;

void readFiles() {
  root = SD.open("/");
  fileCount = 0;
  while (true) {
    File entry = root.openNextFile();
    if (!entry) break;
    String name = entry.name();
    if (!entry.isDirectory() && name.endsWith(".mp3")) {
      files[fileCount++] = name;
    }
    entry.close();
  }
}

void IRAM_ATTR readEncoder() {
  int A = digitalRead(encA);
  if (A != lastA) {
    if (digitalRead(encB) != A) encoderPos++;
    else encoderPos--;
  }
  lastA = A;
}

void drawUI() {
  display.clearDisplay();
  display.setCursor(0, 0);
  for (int i = 0; i < fileCount && i < 5; i++) {
    if (i == currentTrack) display.print(">");
    else display.print(" ");
    display.println(files[i]);
  }
  display.display();
}

void playTrack(int index) {
  if (mp3) {
    mp3->stop();
    delete mp3;
    delete file;
  }
  file = new AudioFileSourceSD(files[index].c_str());
  mp3 = new AudioGeneratorMP3();
  mp3->begin(file, out);
  playing = true;
}

void setup() {
  pinMode(btn1, INPUT_PULLUP);
  pinMode(btn2, INPUT_PULLUP);
  pinMode(btn3, INPUT_PULLUP);
  pinMode(encA, INPUT_PULLUP);
  pinMode(encB, INPUT_PULLUP);
  pinMode(encSW, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(encA), readEncoder, CHANGE);

  Wire.begin(21, 22);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();
  display.display();

  SPI.begin(18, 19, 23, 5);
  SD.begin(5);

  out = new AudioOutputI2S();
  out->SetPinout(26, 25, 22);
  out->begin();

  readFiles();
  drawUI();
}

void loop() {
  if (encoderPos > 0) {
    currentTrack = (currentTrack + 1) % fileCount;
    encoderPos = 0;
    drawUI();
  }

  if (encoderPos < 0) {
    currentTrack = (currentTrack - 1 + fileCount) % fileCount;
    encoderPos = 0;
    drawUI();
  }

  if (!digitalRead(encSW)) {
    delay(200);
    playTrack(currentTrack);
    drawUI();
  }

  if (!digitalRead(btn1)) {
    delay(200);
    playTrack(currentTrack);
  }

  if (!digitalRead(btn2)) {
    delay(200);
    if (playing && mp3) mp3->stop();
    playing = false;
  }

  if (!digitalRead(btn3)) {
    delay(200);
    currentTrack = (currentTrack + 1) % fileCount;
    drawUI();
  }

  if (playing && mp3 && mp3->isRunning()) {
    if (!mp3->loop()) {
      mp3->stop();
      playing = false;
    }
  }
}
