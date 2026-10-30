#include <Arduino.h>
#include <Servo.h>

Servo output;

void setup() {
  Serial.begin(115200);
  pinMode(12, INPUT); // D6, connected to D5 by a jumper
  output.attach(14, 1000, 2000, 1000); // D5
  Serial.println("Pulse diagnostic: connect D5 to D6; battery disconnected");
}

void loop() {
  for (int width : {1000, 1200}) {
    output.writeMicroseconds(width);
    delay(250);
    unsigned long high = pulseIn(12, HIGH, 50000);
    unsigned long low = pulseIn(12, LOW, 50000);
    Serial.printf("command_us=%d high_us=%lu low_us=%lu\n", width, high, low);
  }
  output.writeMicroseconds(1000);
  delay(1000);
}
