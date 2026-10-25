/*
 * Smart Door AI - ESP32 Firmware (Dual Mode: USB Serial + Wi-Fi MQTT, Servo Lock + Relay)
 * Libraries (Library Manager): ESP32Servo, PubSubClient, ArduinoJson (v6.x)
 * Board: "ESP32 Dev Module"
 *
 * 1) USB Serial contract (PySerial / IOT_MODE=serial):
 *    Receives : "UNLOCK" or "UNLOCK:5\n" | "LOCK\n"
 *    Responds : {"state":"unlocked|locked","door":"open|closed","fw":"1.1"}
 *
 * 2) MQTT contract (Mosquitto / IOT_MODE=real):
 *    Subscribe: smartdoor/<DEVICE_ID>/cmd        {"action":"unlock","duration":5} | {"action":"lock"}
 *    Publish  : smartdoor/<DEVICE_ID>/status     {"state":"locked|unlocked","door":"open|closed","fw":"1.1"}
 *    Publish  : smartdoor/<DEVICE_ID>/heartbeat  every 10 s
 *
 * FAIL-SECURE: boots locked (Servo 0 deg / Relay off), relocks locally by timer even if PC/Wi-Fi disconnects.
 */
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>

// ---- CONFIG ----
const char* WIFI_SSID   = "YOUR_WIFI";
const char* WIFI_PASS   = "YOUR_PASSWORD";
const char* MQTT_HOST   = "192.168.1.10";   // PC / server running Mosquitto
const int   MQTT_PORT   = 1883;
const char* DEVICE_ID   = "door01";         // must match MQTT_DEVICE_ID in backend .env
const char* FW_VERSION  = "1.1";
const bool  ENABLE_WIFI = false;            // set true when using MQTT over Wi-Fi; false for USB Serial only

#define SERVO_PIN   18   // Servo signal pin (prototype door lock: 0 deg = locked, 90 deg = unlocked)
#define RELAY_PIN   26   // Relay IN (drives solenoid via isolated relay + flyback diode)
#define LED_PIN     2    // Status LED (on = unlocked)
#define BUZZER_PIN  27
#define REED_PIN    25   // Magnetic door sensor to GND (INPUT_PULLUP)
#define RELAY_ACTIVE_LOW true

#define SERVO_LOCKED_ANGLE   0
#define SERVO_UNLOCKED_ANGLE 90

Servo lockServo;
WiFiClient wifi;
PubSubClient mqtt(wifi);
String topicCmd, topicStatus, topicBeat;

bool unlocked = false;
unsigned long relockAt = 0, lastBeat = 0, lastReconnect = 0;
bool lastDoorOpen = false;
String serialBuf = "";

void relay(bool on) { digitalWrite(RELAY_PIN, (on ^ RELAY_ACTIVE_LOW) ? HIGH : LOW); }

void beep(int ms) { digitalWrite(BUZZER_PIN, HIGH); delay(ms); digitalWrite(BUZZER_PIN, LOW); }

void publishStatus() {
  StaticJsonDocument<160> d;
  d["state"] = unlocked ? "unlocked" : "locked";
  d["door"]  = digitalRead(REED_PIN) == HIGH ? "open" : "closed";
  d["fw"]    = FW_VERSION;
  char buf[160];
  serializeJson(d, buf);
  Serial.println(buf);
  if (ENABLE_WIFI && mqtt.connected()) {
    mqtt.publish(topicStatus.c_str(), buf, true);
  }
}

void setLock(bool open, unsigned long durationMs = 0) {
  unlocked = open;
  lockServo.write(open ? SERVO_UNLOCKED_ANGLE : SERVO_LOCKED_ANGLE);
  relay(open);
  digitalWrite(LED_PIN, open ? HIGH : LOW);
  relockAt = open ? millis() + durationMs : 0;
  beep(open ? 120 : 40);
  publishStatus();
}

void handleSerialCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();
  if (cmd.startsWith("UNLOCK")) {
    int sec = 5;
    int colon = cmd.indexOf(':');
    if (colon > 0) {
      int parsed = cmd.substring(colon + 1).toInt();
      if (parsed >= 1 && parsed <= 60) sec = parsed;
    }
    setLock(true, (unsigned long)sec * 1000UL);
  } else if (cmd == "LOCK") {
    setLock(false);
  } else if (cmd == "STATUS") {
    publishStatus();
  }
}

void onMessage(char* topic, byte* payload, unsigned int len) {
  StaticJsonDocument<128> d;
  if (deserializeJson(d, payload, len)) return;
  const char* action = d["action"] | "";
  if (!strcmp(action, "unlock")) {
    int sec = constrain((int)(d["duration"] | 5), 1, 60);
    setLock(true, sec * 1000UL);
  } else if (!strcmp(action, "lock")) {
    setLock(false);
  }
}

void connectWifi() {
  if (!ENABLE_WIFI) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long t = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t < 10000) delay(250);
}

void connectMqtt() {
  if (!ENABLE_WIFI) return;
  if (WiFi.status() != WL_CONNECTED) { connectWifi(); return; }
  String cid = String("esp32-") + DEVICE_ID;
  if (mqtt.connect(cid.c_str())) {
    mqtt.subscribe(topicCmd.c_str(), 1);
    publishStatus();
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(REED_PIN, INPUT_PULLUP);

  lockServo.attach(SERVO_PIN);
  lockServo.write(SERVO_LOCKED_ANGLE);
  relay(false);                       // locked at boot

  topicCmd    = String("smartdoor/") + DEVICE_ID + "/cmd";
  topicStatus = String("smartdoor/") + DEVICE_ID + "/status";
  topicBeat   = String("smartdoor/") + DEVICE_ID + "/heartbeat";

  if (ENABLE_WIFI) {
    connectWifi();
    mqtt.setServer(MQTT_HOST, MQTT_PORT);
    mqtt.setCallback(onMessage);
  }
  publishStatus();
}

void loop() {
  // 1. Check USB Serial commands (UNLOCK:<sec> / LOCK)
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (serialBuf.length() > 0) {
        handleSerialCommand(serialBuf);
        serialBuf = "";
      }
    } else {
      serialBuf += c;
    }
  }

  // 2. Check Wi-Fi / MQTT if enabled
  if (ENABLE_WIFI) {
    if (!mqtt.connected()) {
      if (millis() - lastReconnect > 3000) { lastReconnect = millis(); connectMqtt(); }
    } else {
      mqtt.loop();
    }
  }

  // 3. Local auto-relock (works offline & in both Serial/MQTT modes)
  if (unlocked && relockAt && (long)(millis() - relockAt) >= 0) setLock(false);

  // 4. Door reed sensor change
  bool doorOpen = digitalRead(REED_PIN) == HIGH;
  if (doorOpen != lastDoorOpen) { lastDoorOpen = doorOpen; publishStatus(); }

  // 5. Periodic heartbeat
  if (ENABLE_WIFI && mqtt.connected() && millis() - lastBeat > 10000) {
    lastBeat = millis();
    StaticJsonDocument<128> d;
    d["state"] = unlocked ? "unlocked" : "locked";
    d["fw"] = FW_VERSION;
    char buf[128];
    serializeJson(d, buf);
    mqtt.publish(topicBeat.c_str(), buf);
  }
}
