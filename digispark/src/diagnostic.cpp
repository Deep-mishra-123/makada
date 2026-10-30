#include <Arduino.h>

void setup() {
  pinMode(2, INPUT); // NodeMCU signal, no pull-up to 5 V
  pinMode(1, OUTPUT); // onboard LED, active high on common Digispark boards
  digitalWrite(1, LOW);
}

void loop() {
  const unsigned long pulse = pulseIn(2, HIGH, 30000UL);
  if (pulse >= 850 && pulse <= 2100) {
    digitalWrite(1, (millis() / 250) % 2);
  } else {
    digitalWrite(1, LOW);
  }
}
