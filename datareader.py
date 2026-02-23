/*
 * HOSA EKG Project - Handheld ECG Monitor
 * Features: 
 * 1. Real-time ECG Waveform output (Serial Plotter)
 * 2. Beat Detection (BPM)
 * 3. Heart Rate Variability (RMSSD)
 * 4. Leads-Off Detection (Impedance Check)
 */

const int SENSOR_PIN = A0; // Signal pin from AD8232
const int LO_PLUS = 10;    // Leads Off + pin
const int LO_MINUS = 11;   // Leads Off - pin

// Tuning Variables (You might need to tweak these!)
int threshold = 550;       // Signal height to count as a beat (0-1023)
int hysteresis = 100;      // How much signal must drop to reset beat
long refractoryPeriod = 300; // Minimum ms between beats (prevents double counting)

// System Variables
long lastBeatTime = 0;
float bpm = 0;
float rrIntervals[10];     // Store last 10 heartbeats for HRV
int rrIndex = 0;
boolean isPeak = false;

void setup() {
  Serial.begin(9600);
  pinMode(LO_PLUS, INPUT);
  pinMode(LO_MINUS, INPUT);
}

void loop() {
  // 1. SKIN IMPEDANCE CHECK (Leads Off Detection)
  // If LO+ or LO- is HIGH, the pads aren't touching skin properly.
  if (digitalRead(LO_PLUS) == 1 || digitalRead(LO_MINUS) == 1) {
    Serial.println("!,0,0,0"); // "!" tells the app/screen "LEADS OFF"
    delay(100); 
    return; // Skip the rest of the loop
  }

  // 2. READ & FILTER SIGNAL
  int rawValue = analogRead(SENSOR_PIN);
  
  // Simple "Moving Average" filter to smooth out jitter
  static int filteredValue = 0;
  filteredValue = (0.8 * filteredValue) + (0.2 * rawValue);

  // 3. BEAT DETECTION ALGORITHM
  long currentTime = millis();
  
  // Check if signal is above threshold AND enough time has passed since last beat
  if (filteredValue > threshold && !isPeak && (currentTime - lastBeatTime > refractoryPeriod)) {
    
    // WE FOUND A BEAT!
    long rrInterval = currentTime - lastBeatTime;
    lastBeatTime = currentTime;
    isPeak = true; 

    // Calculate BPM
    bpm = 60000.0 / rrInterval;

    // Store RR Interval for HRV calculation
    rrIntervals[rrIndex] = rrInterval;
    rrIndex = (rrIndex + 1) % 10; // Loop back to 0 after 10 beats

    // Calculate HRV (RMSSD)
    float hrv = calculateRMSSD();

    // PRINT DATA for Serial Plotter
    // Format: Signal, Threshold, BPM, HRV
    Serial.print(filteredValue);
    Serial.print(",");
    Serial.print(threshold); // Plot threshold line for visual ref
    Serial.print(",");
    Serial.print(bpm);
    Serial.print(",");
    Serial.println(hrv);
  
  } else if (filteredValue < (threshold - hysteresis)) {
    // Signal dropped low enough to be ready for next beat
    isPeak = false;
    
    // Just print the waveform so the line keeps drawing
    Serial.print(filteredValue);
    Serial.print(",");
    Serial.print(threshold);
    Serial.println(",,"); // Empty commas to keep format consistent
  } else {
    // In between states
    Serial.print(filteredValue);
    Serial.print(",");
    Serial.print(threshold);
    Serial.println(",,");
  }
  
  delay(10); // Small delay to keep things stable (approx 100Hz sampling)
}

// 4. HRV ALGORITHM (Root Mean Square of Successive Differences)
float calculateRMSSD() {
  float sumSquaredDiffs = 0;
  int validCounts = 0;
  
  for (int i = 0; i < 9; i++) {
    // Ignore empty slots (0) in the array at startup
    if (rrIntervals[i] > 0 && rrIntervals[i+1] > 0) {
      float diff = rrIntervals[i] - rrIntervals[i+1];
      sumSquaredDiffs += (diff * diff);
      validCounts++;
    }
  }
  
  if (validCounts > 0) {
    return sqrt(sumSquaredDiffs / validCounts);
  } else {
    return 0; // Not enough data yet
  }
}
