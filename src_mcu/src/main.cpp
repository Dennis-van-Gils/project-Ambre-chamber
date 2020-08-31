/*******************************************************************************
  Ambre chamber

  Adafruit Feather M4 Express
    DHT22
        Reads out temperature and humidity.

    DS18B20
        Reads out temperature.

    Solenoid valve
        Controls either a dry N2 air flow or a humid air flow, depending what
        the user needs at that moment.

        We define:
            humi_threshold:
                Threshold in the humidity value above or below which the valve
                should open.

            open_valve_when_super_humi:
                Boolean. Should the valve open when the humidity is above the
                threshold (true) or below the threshold (false).

  The RGB LED of the Feather M4 will indicate its status:
  * Blue : We're setting up
  * Green: Running okay
  * Red  : Communication error
  Every update, the LED will alternate in brightness.

  Dennis van Gils
  31-08-2020
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
float ds18_temp(NAN);        // Temperature       ['C]
float dht22_humi(NAN);       // Relative humidity [%]
float dht22_temp(NAN);       // Temperature       ['C]
bool is_valve_open = false;  // State of the solenoid valve

float humi_threshold = 50;   // Humidity threshold [%]
bool open_valve_when_super_humi = true;

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
    static bool toggle_LED = false;

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
        if (toggle_LED) {
            neo.setBrightness(NEO_BRIGHT);
        } else {
            neo.setBrightness(NEO_DIM);
        }
        neo.show();
        toggle_LED = !toggle_LED;
    }

    // Automatic control of the valve depending on the humidity
    if (isnan(dht22_humi)) {
        is_valve_open = false;
        digitalWrite(PIN_SOLENOID_VALVE, LOW);
    } else {
        if (
            ((dht22_humi > humi_threshold) && open_valve_when_super_humi) ||
            ((dht22_humi < humi_threshold) && !open_valve_when_super_humi)
           ) {
            is_valve_open = true;
            digitalWrite(PIN_SOLENOID_VALVE, HIGH);
        } else {
            is_valve_open = false;
            digitalWrite(PIN_SOLENOID_VALVE, LOW);
        }
    }

    if (sc.available()) {
        strCmd = sc.getCmd();

        if (strcmp(strCmd, "id?") == 0) {
            Serial.println("Arduino, Ambre chamber");

        } else if (strcmp(strCmd, "th?") == 0) {
            // Get humidity threshold
            Serial.println(humi_threshold, 0);

        } else if (strncmp(strCmd, "th", 2) == 0) {
            // Set humidity threshold
            humi_threshold = constrain(parseFloatInString(strCmd, 2), 0, 100);

        } else if (strcmp(strCmd, "open when super humi") == 0) {
            open_valve_when_super_humi = true;

        } else if (strcmp(strCmd, "open when sub humi") == 0) {
            open_valve_when_super_humi = false;

        /*
        } else if (strcmp(strCmd, "0") == 0) {
            is_valve_open = false;
            digitalWrite(PIN_SOLENOID_VALVE, LOW);

        } else if (strcmp(strCmd, "1") == 0) {
            is_valve_open = true;
            digitalWrite(PIN_SOLENOID_VALVE, HIGH);
        */

        } else {
            Serial.println(
                String(ds18_tick) +
                '\t' + String(ds18_temp, 1) +
                '\t' + String(dht22_temp, 1)+
                '\t' + String(dht22_humi, 1) +
                '\t' + String(is_valve_open));
        }
    }
}
