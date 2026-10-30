#include <Arduino.h>

// NodeMCU D5 -> P2; P1 -> ESC signal. Power the ATtiny at verified 5 V.
// Forward only plausible pulse widths. Silence the output on missing/invalid input.
constexpr uint8_t INPUT_PIN = 2;
constexpr uint8_t OUTPUT_PIN = 1;

void setup() {
  digitalWrite(OUTPUT_PIN, LOW);
  pinMode(OUTPUT_PIN, OUTPUT);
  pinMode(INPUT_PIN, INPUT); // no pull-up to 5 V on the ESP8266 connection
}

void loop() {
  unsigned long width = pulseIn(INPUT_PIN, HIGH, 30000UL);
  if (width >= 850 && width <= 2100) {
    digitalWrite(OUTPUT_PIN, HIGH);
    delayMicroseconds(width);
    digitalWrite(OUTPUT_PIN, LOW);
  } else {
    digitalWrite(OUTPUT_PIN, LOW);
  }
}
