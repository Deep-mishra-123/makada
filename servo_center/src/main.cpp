#include <Arduino.h>
#include <Servo.h>

Servo servos[3];
constexpr int pins[] = {14, 12, 13}; // D5, D6, D7

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 3; ++i) {
    servos[i].attach(pins[i], 1000, 2000, 1500);
  }
  Serial.println("CENTER D5 D6 D7 pulse_us=1500");
}

void loop() {
  if (Serial.available()) {
    while (Serial.available()) Serial.read();
    Serial.println("CENTER D5 D6 D7 pulse_us=1500");
  }
  delay(10);
}
