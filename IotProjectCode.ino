#include <ESP8266WiFi.h>
#include <SPI.h>
#include <Wire.h>
#include "MQ135.h"
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

String apiKey = "OS23YE6OLEUW3UOC";
const char* ssid = "OnePlus 9R";
const char* pass = "Bharatpur";
const char* server = "api.thingspeak.com";

WiFiClient client;
MQ135 gasSensor(A0);

#define DHTPIN D2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("SSD1306 allocation failed"));
    while(true);
  }
  display.clearDisplay();
  delay(10);

  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, pass);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");

  display.clearDisplay();
  display.setCursor(0,0);
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.println("WiFi connected");
  display.display();
  delay(2000);

  dht.begin();
}

void loop() {
  float air_quality = gasSensor.getPPM();
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT sensor!");
    humidity = 0.0;
    temperature = 0.0;
  }

  Serial.print("Air Quality: ");
  Serial.print(air_quality);
  Serial.println(" PPM");

  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");

  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.println(" *C");

  // OLED display update
  display.clearDisplay();
  display.setCursor(0,0);
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.println("Air Quality Index:");
  display.setTextSize(2);
  display.println(air_quality);

  display.setTextSize(1);
  display.println();
  display.print("Humidity: ");
  display.print(humidity);
  display.println(" %");

  display.print("Temp: ");
  display.print(temperature);
  display.println(" C");

  display.display();

  // Send data to ThingSpeak
  if (client.connect(server, 80)) {
    String postStr = "api_key=" + apiKey;
    postStr += "&field1=" + String(air_quality);
    postStr += "&field2=" + String(humidity);
    postStr += "&field3=" + String(temperature);

    client.print("POST /update HTTP/1.1\r\n");
    client.print("Host: api.thingspeak.com\r\n");
    client.print("Connection: close\r\n");
    client.print("Content-Type: application/x-www-form-urlencoded\r\n");
    client.print("Content-Length: ");
    client.print(postStr.length());
    client.print("\r\n\r\n");
    client.print(postStr);

    Serial.println("Sending data to ThingSpeak...");

    unsigned long timeout = millis();
    while (client.available() == 0) {
      if (millis() - timeout > 5000) {
        Serial.println(">>> Client Timeout !");
        client.stop();
        return;
      }
    }

    while(client.available()) {
      String line = client.readStringUntil('\r');
      Serial.print(line);
    }

    Serial.println("\nData sent to ThingSpeak.");
  } else {
    Serial.println("Connection to ThingSpeak failed");
  }

  client.stop();

  Serial.println("Waiting 15 seconds before next update...");
  delay(15000);
}
