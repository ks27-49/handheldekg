/*
 * HOSA V3 Single-Site ECG Patch
 * Features: 
 * - Three electrodes: E1 (active 1), E2 (active 2), E3 (reference/ground)
 * - Single-vector ECG output (approximates Lead I, Lead II, V3)
 * - Beat Detection (BPM)
 * - Heart Rate Variability (RMSSD)
 * - Leads-Off Detection (Impedance Check)
 */

const int E1_PIN = A0;  // Active electrode 1
const int E2_PIN = A1;  // Active electrode 2
const int E3_PIN = A2;  // Reference/Ground electrode

const int LO_PLUS = 10;   // Leads-Off + pin
const int LO_MINUS = 11;  // Leads-Off - pin

// Tuning Variables
int threshold = 550;          // Beat detection threshold
int hysteresis = 100;         // Signal drop needed to reset peak
long refractoryPeriod = 300;  // Minimum ms between beats

// System Variables
long lastBeatTime = 0;
float bpm = 0;
float rrIntervals[10]; // Last 10 RR intervals
int rrIndex = 0;
boolean isPeak = false;

void setup() {
  Serial.begin(9600);
  pinMode(LO_PLUS, INPUT);
  pinMode(LO_MINUS, INPUT);
}

void loop() {
  // 1. Leads-Off Detection
  if (digitalRead(LO_PLUS) == 1 || digitalRead(LO_MINUS) == 1) {
    Serial.println("!,0,0,0,0,0"); // "!": leads-off
    delay(100);
    return;
  }

  // 2. Read Signals
  int e1 = analogRead(E1_PIN);
  int e2 = analogRead(E2_PIN);
  int e3 = analogRead(E3_PIN); // ground/reference

  // 3. Compute "Single Vector ECG"
  // Lead I approximation: E2 - E3
  int leadI = e2 - e3;
  // Lead II approximation: E1 - E3
  int leadII = e1 - e3;
  // V3 vector: weighted combination (single-site trend)
  int v3 = ((leadI + leadII) / 2);

  // 4. Moving average filter for V3
  static float filteredV3 = 0;
  filteredV3 = (0.8 * filteredV3) + (0.2 * v3);

  // 5. Beat Detection
  long currentTime = millis();
  if (filteredV3 > threshold && !isPeak && (currentTime - lastBeatTime > refractoryPeriod)) {
    long rrInterval = currentTime - lastBeatTime;
    lastBeatTime = currentTime;
    isPeak = true;

    bpm = 60000.0 / rrInterval;

    rrIntervals[rrIndex] = rrInterval;
    rrIndex = (rrIndex + 1) % 10;

    float hrv = calculateRMSSD();

    // Serial output: Lead I, Lead II, V3, Threshold, BPM, HRV
    Serial.print(leadI);
    Serial.print(",");
    Serial.print(leadII);
    Serial.print(",");
    Serial.print(filteredV3);
    Serial.print(",");
    Serial.print(threshold);
    Serial.print(",");
    Serial.print(bpm);
    Serial.print(",");
    Serial.println(hrv);

  } else if (filteredV3 < (threshold - hysteresis)) {
    isPeak = false;
    // Just print waveform to keep line plotting
    Serial.print(leadI);
    Serial.print(",");
    Serial.print(leadII);
    Serial.print(",");
    Serial.print(filteredV3);
    Serial.print(",");
    Serial.print(threshold);
    Serial.println(",,"); // Empty BPM, HRV
  } else {
    Serial.print(leadI);
    Serial.print(",");
    Serial.print(leadII);
    Serial.print(",");
    Serial.print(filteredV3);
    Serial.print(",");
    Serial.print(threshold);
    Serial.println(",,"); // Empty BPM, HRV
  }

  delay(10); // ~100Hz sampling
}

// HRV: RMSSD calculation
float calculateRMSSD() {
  float sumSquaredDiffs = 0;
  int validCounts = 0;

  for (int i = 0; i < 9; i++) {
    if (rrIntervals[i] > 0 && rrIntervals[i+1] > 0) {
      float diff = rrIntervals[i] - rrIntervals[i+1];
      sumSquaredDiffs += (diff * diff);
      validCounts++;
    }
  }

  if (validCounts > 0) {
    return sqrt(sumSquaredDiffs / validCounts);
  } else {
    return 0;
  }
}
