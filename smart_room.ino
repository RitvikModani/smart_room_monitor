// ESP32_Room_Controller.ino
#define LED_PIN     14
#define MOTOR_IN1   27
#define MOTOR_IN2   26
#define MOTOR_PWM   33

int motorSpeed = 180;  // 0-255

void setup() {
  Serial.begin(115200);
  
  pinMode(LED_PIN, OUTPUT);
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_PWM, OUTPUT);
  
  digitalWrite(LED_PIN, LOW);
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  
  Serial.println("ESP32 Room Controller Ready");
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "LIGHT_ON") {
      digitalWrite(LED_PIN, HIGH);
      Serial.println("LIGHT:ON");
    }
    else if (command == "LIGHT_OFF") {
      digitalWrite(LED_PIN, LOW);
      Serial.println("LIGHT:OFF");
    }
    else if (command == "FAN_ON") {
      digitalWrite(MOTOR_IN1, HIGH);
      digitalWrite(MOTOR_IN2, LOW);
      analogWrite(MOTOR_PWM, motorSpeed);
      Serial.println("FAN:ON");
    }
    else if (command == "FAN_OFF") {
      digitalWrite(MOTOR_IN1, LOW);
      digitalWrite(MOTOR_IN2, LOW);
      analogWrite(MOTOR_PWM, 0);
      Serial.println("FAN:OFF");
    }
    else if (command.startsWith("FAN_SPEED:")) {
      motorSpeed = command.substring(10).toInt();
      motorSpeed = constrain(motorSpeed, 0, 255);
      Serial.println("SPEED:" + String(motorSpeed));
    }
  }
}