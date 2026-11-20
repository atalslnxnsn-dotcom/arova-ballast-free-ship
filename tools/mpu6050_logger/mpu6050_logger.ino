// MPU6050 roll/pitch logger for the Arova model ship - prints CSV "t,roll,pitch" at ~100 Hz over USB serial.
// Wiring: UNO/Nano SDA=A4 SCL=A5 VCC=5V; ESP32 SDA=21 SCL=22 VCC=3V3. X axis to the bow.
// Keep the model level and still for 2 s after reset (gyro bias + mounting offset calibration).
// Not compiled or tested on hardware yet - bench-check against a phone inclinometer at 0 and +-10 deg.

#include <Wire.h>
const int MPU = 0x68;
float roll = 0, pitch = 0, gxo = 0, gyo = 0, r0 = 0, p0 = 0;
const float A = 0.98;                 // gyro weight; 0.96-0.98 typical
unsigned long tPrev;

void readRaw(int16_t *v) {            // ax,ay,az,temp,gx,gy,gz
  Wire.beginTransmission(MPU); Wire.write(0x3B); Wire.endTransmission(false);
  Wire.requestFrom(MPU, 14, true);
  for (int i = 0; i < 7; i++) v[i] = (Wire.read() << 8) | Wire.read();
}
void wr(byte reg, byte val) { Wire.beginTransmission(MPU); Wire.write(reg); Wire.write(val); Wire.endTransmission(true); }

void setup() {
  Serial.begin(115200); Wire.begin(); Wire.setClock(400000);
  wr(0x6B, 0x00);                     // wake
  wr(0x1A, 0x03);                     // DLPF ~44 Hz accel / 42 Hz gyro
  wr(0x1B, 0x00); wr(0x1C, 0x00);     // ±250 dps, ±2 g
  // calibration: keep the model level and still for ~2 s
  int16_t v[7]; float sr = 0, sp = 0;
  for (int i = 0; i < 200; i++) {
    readRaw(v);
    gxo += v[4] / 131.0; gyo += v[5] / 131.0;
    sr += atan2((float)v[1], (float)v[2]) * 57.2958;
    sp += atan2(-(float)v[0], sqrt((float)v[1]*v[1] + (float)v[2]*v[2])) * 57.2958;
    delay(5);
  }
  gxo /= 200; gyo /= 200; r0 = sr / 200; p0 = sp / 200;   // gyro bias + mounting offset
  roll = 0; pitch = 0;
  Serial.println("t,roll,pitch");
  tPrev = micros();
}

void loop() {
  int16_t v[7]; readRaw(v);
  unsigned long now = micros(); float dt = (now - tPrev) * 1e-6; tPrev = now;
  float ax = v[0], ay = v[1], az = v[2];
  float accR = atan2(ay, az) * 57.2958 - r0;
  float accP = atan2(-ax, sqrt(ay*ay + az*az)) * 57.2958 - p0;
  roll  = A * (roll  + (v[4]/131.0 - gxo) * dt) + (1 - A) * accR;
  pitch = A * (pitch + (v[5]/131.0 - gyo) * dt) + (1 - A) * accP;
  Serial.print(now / 1e6, 3); Serial.print(','); Serial.print(roll, 2); Serial.print(','); Serial.println(pitch, 2);
  delay(8);                           // ~100 Hz incl. I2C + print time
}
