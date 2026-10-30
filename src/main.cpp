#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <Servo.h>
#include "secrets.h"
#if __has_include("cute_clip.h")
#include "cute_clip.h"
#else
// Private sampled audio is excluded from the public repository.
const uint8_t cuteClip[] PROGMEM = {128};
#endif
#include <stdlib.h>
#include <string.h>

// Bench firmware: pulse widths are commands, not measured speed or power.
constexpr int SIGNAL_PIN = 14; // NodeMCU D5
constexpr int WIFI_LED_PIN = LED_BUILTIN; // GPIO2, active low on NodeMCU
constexpr int MOTOR_LED_PIN = 16; // D0: second active-low LED on standard DevKit
constexpr int BUZZER_PIN = 5; // D1, small passive piezo
constexpr int STOP_US = 1000;
int idleUs = STOP_US;
constexpr int MAX_US = 2000;
int limitUs = 1100;
constexpr uint32_t LINK_TIMEOUT_MS = 750;
constexpr uint32_t MAX_ARM_MS = 3000;
Servo esc;
bool armed = false;
int pulseUs = STOP_US;
uint32_t lastHeartbeat = 0;
uint32_t armedAt = 0;
char line[64];
size_t used = 0;
bool overflow = false;
WiFiServer server(8266);
WiFiClient controller;
bool authenticated = false;
bool networkOwner = false;
uint32_t connectedAt = 0;
char networkLine[96];
size_t networkUsed = 0;
bool networkOverflow = false;
Print *response = &Serial;
void enforceTimeouts();

void updateIndicators() {
  const uint32_t now = millis();
  const bool wifiOn = WiFi.status() == WL_CONNECTED || (now / 300) % 2 == 0;
  const bool motorOn = armed && pulseUs > STOP_US && (now / 125) % 2 == 0;
  digitalWrite(WIFI_LED_PIN, wifiOn ? LOW : HIGH);
  digitalWrite(MOTOR_LED_PIN, motorOn ? LOW : HIGH);
}

void stop(const char *reason) {
  armed = false;
  pulseUs = idleUs;
  esc.writeMicroseconds(idleUs);
  updateIndicators();
  Serial.printf("STOP %s\n", reason);
  if (authenticated && controller.connected()) controller.printf("STOP %s\n", reason);
}

void status() {
  response->printf("STATUS firmware=cutie-bench-wifi-v4 armed=%d pulse_us=%d limit_us=%d uptime_ms=%lu wifi=%d ip=%s motor_led_active=%d\n",
                armed, pulseUs, limitUs, millis(), WiFi.status() == WL_CONNECTED,
                WiFi.localIP().toString().c_str(), armed && pulseUs > STOP_US);
}

void handle(const char *command, bool fromNetwork = false) {
  if (strcmp(command, "STATUS") == 0) {
    status();
  } else if (strcmp(command, "CLIP") == 0) {
    if (armed) {
      response->println("ERR CLIP armed");
      return;
    }
    noTone(BUZZER_PIN);
    analogWriteFreq(31250);
    analogWriteRange(255);
    uint32_t next = micros();
    for (size_t i = 0; i < sizeof(cuteClip); ++i) {
      analogWrite(BUZZER_PIN, pgm_read_byte(&cuteClip[i]));
      next += 125;
      while (static_cast<int32_t>(next - micros()) > 0) {
        if (next - micros() > 500) yield();
      }
      if ((i & 63) == 0) {
        yield();
        if (fromNetwork && !controller.connected()) break;
      }
    }
    analogWrite(BUZZER_PIN, 0);
    response->println("OK CLIP");
  } else if (strncmp(command, "BEEP ", 5) == 0) {
    char *end = nullptr;
    long frequency = strtol(command + 5, &end, 10);
    if (end == command + 5 || *end != ' ') {
      response->println("ERR BEEP");
      return;
    }
    char *durationEnd = nullptr;
    long duration = strtol(end + 1, &durationEnd, 10);
    if (durationEnd == end + 1 || *durationEnd != '\0' ||
        frequency < 200 || frequency > 2000 || duration < 1 || duration > 500) {
      response->println("ERR BEEP");
      return;
    }
    tone(BUZZER_PIN, static_cast<unsigned int>(frequency), static_cast<unsigned long>(duration));
    response->printf("OK BEEP %ld %ld\n", frequency, duration);
  } else if (strcmp(command, "STOP") == 0) {
    stop("requested");
  } else if (strncmp(command, "IDLE ", 5) == 0) {
    char *end = nullptr;
    const long value = strtol(command + 5, &end, 10);
    if (armed || end == command + 5 || *end != '\0' || value < 900 || value > 1000) {
      stop("idle_rejected");
      return;
    }
    idleUs = static_cast<int>(value);
    pulseUs = idleUs;
    esc.writeMicroseconds(idleUs);
    response->printf("OK IDLE %d\n", idleUs);
  } else if (strcmp(command, "ARM") == 0) {
    if (armed || millis() < 3000) {
      stop("arm_rejected");
      return;
    }
    pulseUs = idleUs;
    esc.writeMicroseconds(idleUs);
    armed = true;
    networkOwner = fromNetwork;
    armedAt = lastHeartbeat = millis();
    response->println("OK ARM");
  } else if (strcmp(command, "PING") == 0) {
    if (armed && networkOwner == fromNetwork) lastHeartbeat = millis();
    response->println("OK PING");
  } else if (strncmp(command, "LIMIT ", 6) == 0) {
    char *end = nullptr;
    const long value = strtol(command + 6, &end, 10);
    if (armed || end == command + 6 || *end != '\0' || value < STOP_US || value > MAX_US) {
      stop("limit_rejected");
      return;
    }
    limitUs = static_cast<int>(value);
    response->printf("OK LIMIT %d\n", limitUs);
  } else if (strncmp(command, "SET ", 4) == 0) {
    char *end = nullptr;
    const long value = strtol(command + 4, &end, 10);
    if (!armed || networkOwner != fromNetwork || end == command + 4 || *end != '\0' ||
        value < STOP_US || value > limitUs) {
      stop("set_rejected");
      return;
    }
    pulseUs = static_cast<int>(value);
    esc.writeMicroseconds(pulseUs);
    updateIndicators();
    response->printf("OK SET %d\n", pulseUs);
  } else {
    stop("invalid_command");
  }
}

void serviceNetwork() {
  static bool wasConnected = false;
  const bool connected = WiFi.status() == WL_CONNECTED;
  if (connected != wasConnected) {
    if (!connected) stop("wifi_lost");
    else Serial.printf("WIFI connected ip=%s\n", WiFi.localIP().toString().c_str());
    wasConnected = connected;
  }
  if (authenticated && !controller.connected()) {
    if (authenticated && armed && networkOwner) stop("controller_lost");
    controller.stop();
    authenticated = false;
  }
  if (server.hasClient()) {
    WiFiClient incoming = server.accept();
    if (controller.connected()) {
      incoming.stop(); // One controller; never replace the active session.
    } else {
      controller = incoming;
      controller.setNoDelay(true);
      controller.setTimeout(100);
      authenticated = false;
      connectedAt = millis();
      networkUsed = 0;
      networkOverflow = false;
    }
  }
  if (controller.connected() && !authenticated && millis() - connectedAt > 5000) {
    controller.stop();
  }
  for (int count = 0; count < 64 && controller.connected() && controller.available(); ++count) {
    const char ch = controller.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      if (!networkOverflow && networkUsed) {
        networkLine[networkUsed] = '\0';
        if (!authenticated) {
          if (strncmp(networkLine, "AUTH ", 5) == 0 && strcmp(networkLine + 5, BENCH_TOKEN) == 0) {
            stop("network_session");
            authenticated = true;
            controller.println("OK AUTH");
          } else {
            controller.println("ERR AUTH");
            controller.stop();
          }
        } else {
          response = &controller;
          handle(networkLine, true);
          response = &Serial;
        }
      }
      networkUsed = 0;
      networkOverflow = false;
    } else if (!networkOverflow) {
      if (networkUsed < sizeof(networkLine) - 1 && ch >= 32 && ch <= 126) {
        networkLine[networkUsed++] = ch;
      } else {
        networkOverflow = true;
        if (authenticated) stop("invalid_line");
        else controller.stop();
      }
    }
    enforceTimeouts();
  }
}

void enforceTimeouts() {
  const uint32_t now = millis();
  if (armed && now - lastHeartbeat >= LINK_TIMEOUT_MS) stop("link_timeout");
  if (armed && now - armedAt >= MAX_ARM_MS) stop("bench_time_limit");
}

void setup() {
  digitalWrite(WIFI_LED_PIN, HIGH);
  pinMode(WIFI_LED_PIN, OUTPUT);
  digitalWrite(MOTOR_LED_PIN, HIGH);
  pinMode(MOTOR_LED_PIN, OUTPUT);
  // Set the initial pulse explicitly: Servo's default neutral would be too high.
  esc.attach(SIGNAL_PIN, 900, MAX_US, STOP_US);
  Serial.begin(115200);
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(BENCH_SSID, BENCH_PASSWORD);
  server.begin();
  server.setNoDelay(true);
  Serial.println("READY cutie-bench-wifi-v4");
  status();
}

void loop() {
  enforceTimeouts();
  serviceNetwork();
  updateIndicators();
  // Bound serial processing so traffic cannot starve the timeout check.
  for (int count = 0; count < 64 && Serial.available(); ++count) {
    const char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      if (!overflow && used) {
        line[used] = '\0';
        handle(line);
      }
      used = 0;
      overflow = false;
    } else if (!overflow) {
      if (used < sizeof(line) - 1 && ch >= 32 && ch <= 126) {
        line[used++] = ch;
      } else {
        overflow = true;
        stop("invalid_line");
      }
    }
    enforceTimeouts();
  }
  delay(1);
}
