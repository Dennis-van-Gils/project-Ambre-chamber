/*******************************************************************************
  Ambre chamber

  Adafruit Feather M4 Express
    DHT22
        Reads out temperature and humidity.

    DS18B20
        Reads out temperature.

    Solenoid valve
        Controls N2 flow.

  The RGB LED of the Feather M4 will indicate its status:
  * Blue : We're setting up
  * Green: Running okay
  * Red  : Communication error
  Every update, the LED will alternate in brightness.

  Dennis van Gils
  21-08-2020
*******************************************************************************/

#include <Arduino.h>
#include <DvG_SerialCommand.h>
#include <Adafruit_NeoPixel.h>

// DS18B20
#include <OneWire.h>
#include <DallasTemperature.h>

// DHT22
#include <DHT.h>

DvG_SerialCommand sc(Serial); // Instantiate serial command listener

Adafruit_NeoPixel neo(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);
#define NEO_DIM 3  // Brightness level for dim intensity [0 -255]
#define NEO_BRIGHT 8 // Brightness level for bright intensity [0 - 255]

#define PIN_DS18B20 5
#define PIN_DHT22 6
#define PIN_SOLENOID_VALVE 12

OneWire oneWire(PIN_DS18B20);
DallasTemperature ds18(&oneWire);
DHT dht(PIN_DHT22, DHT22);  // Instantiate the DHT22

#define UPDATE_PERIOD_DS18B20 1000  // [ms]
#define UPDATE_PERIOD_DHT22 2000    // [ms]
float ds18_temp(NAN);     // Temperature       ['C]
float dht22_humi(NAN);    // Relative humidity [%]
float dht22_temp(NAN);    // Temperature       ['C]

// -----------------------------------------------------------------------------
//    setup
// -----------------------------------------------------------------------------

void setup() {
    pinMode(PIN_SOLENOID_VALVE, OUTPUT);
    digitalWrite(PIN_SOLENOID_VALVE, LOW);

    neo.begin();
    neo.setPixelColor(0, neo.Color(0, 0, 255)); // Blue: We're in setup()
    neo.setBrightness(NEO_BRIGHT);
    neo.show();

    Serial.begin(9600);
    ds18.begin();
    dht.begin();

    // Have first readings ready
    ds18.requestTemperatures();
    ds18_temp = ds18.getTempCByIndex(0);
    dht22_humi = dht.readHumidity();
    dht22_temp = dht.readTemperature();

    neo.setPixelColor(0, neo.Color(0, 255, 0)); // Green: All set up
    neo.setBrightness(NEO_BRIGHT);
    neo.show();
}

// -----------------------------------------------------------------------------
//    loop
// -----------------------------------------------------------------------------

void loop() {
    char *strCmd; // Incoming serial command string
    uint32_t now = millis();
    static uint32_t dht22_tick = 0;
    static uint32_t ds18_tick = 0;
    static bool toggle = false;

    if (now - dht22_tick >= UPDATE_PERIOD_DHT22) {
        // The DHT22 sensor will report the average temperature and humidity
        // over 2 seconds. It's a slow sensor.
        dht22_tick = now;
        dht22_humi = dht.readHumidity();
        dht22_temp = dht.readTemperature();
    }

    if (now - ds18_tick >= UPDATE_PERIOD_DS18B20) {
        ds18_tick = now;
        ds18.requestTemperatures();
        ds18_temp = ds18.getTempCByIndex(0);

        if (ds18_temp <= -126) {
            ds18_temp = NAN;
        }

        if (isnan(dht22_humi) || isnan(dht22_temp) || isnan(ds18_temp)) {
            neo.setPixelColor(0, neo.Color(255, 0, 0)); // Red: Error
        } else {
            neo.setPixelColor(0, neo.Color(0, 255, 0)); // Green: Okay
        }

        // Heartbeat LED
        if (toggle) {
            neo.setBrightness(NEO_BRIGHT);
        } else {
            neo.setBrightness(NEO_DIM);
        }
        neo.show();
        toggle = !toggle;

        Serial.println(
                String(ds18_tick) +
                '\t' + String(ds18_temp, 1) +
                '\t' + String(dht22_temp, 1)+
                '\t' + String(dht22_humi, 1));
    }

    if (sc.available()) {
        strCmd = sc.getCmd();

        if (strcmp(strCmd, "id?") == 0) {
            Serial.println("Arduino, Ambre chamber");

        } else if(strcmp(strCmd, "0") == 0) {
            digitalWrite(PIN_SOLENOID_VALVE, LOW);

        } else if(strcmp(strCmd, "1") == 0) {
            digitalWrite(PIN_SOLENOID_VALVE, HIGH);

        } else {
            Serial.println(
                String(ds18_tick) +
                '\t' + String(ds18_temp, 1) +
                '\t' + String(dht22_temp, 1)+
                '\t' + String(dht22_humi, 1));
        }
    }
}
