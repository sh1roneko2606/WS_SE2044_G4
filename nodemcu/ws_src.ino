#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
// pin on board
#define DHTPIN D4
#define DHTTYPE DHT11
#define RAIN_PWR D6

//this is use to test this code when i don't have my hardware
const bool HAS_DHT11 = true;
//network and connection
const char* ssid = "Shironeko";
const char* pass = "06062006";                       
const char* mqtt_server = "172.20.10.5";                 
const char* topic = "weather/data";
//cal for rain sensor reading
const int DRY_VAL = 1024;   
const int WET_VAL = 300;    
//object ini
DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient mqtt(espClient);
unsigned long lastSend = 0;
//rain percentage from rain sensor, looping on/off to save battery, and mapping dry value to 0%, wet value to 100%
int readRainPct() {
  digitalWrite(RAIN_PWR, HIGH);
  delay(100);
  int raw = analogRead(A0);
  digitalWrite(RAIN_PWR, LOW);
  return constrain(map(raw, DRY_VAL, WET_VAL, 0, 100), 0, 100);
}
//verify connection, setting the board to station mode
void connectWifi() {
  Serial.print("Connecting to Wi-Fi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nWiFi connected");
  Serial.print("Board IP:  ");
  Serial.println(WiFi.localIP());
  Serial.print("Broker IP: ");
  Serial.println(mqtt_server);

  //warn if the broker is on a different network than this board
  IPAddress broker;
  if (broker.fromString(mqtt_server)) {
    uint32_t mask = (uint32_t)WiFi.subnetMask();
    if (((uint32_t)WiFi.localIP() & mask) != ((uint32_t)broker & mask)) {
      Serial.println("WARNING: broker IP is on a different network than the board!");
    }
  }
}
//connect-reconnect to broker, looping code for connect to wifi first then run the rest
void connectMqtt() {
  while (!mqtt.connected()) {
    if (WiFi.status() != WL_CONNECTED) return;  
    Serial.print("MQTT connecting to ");
    Serial.print(mqtt_server);
    Serial.print(":1883 ... ");
//show weather-node connected on logs to confirm that the board is connected to mqtt broker
    if (mqtt.connect("weather-node")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, state=");
      Serial.print(mqtt.state());
//2s before retry connecting
      Serial.println("  (-2 = cannot reach broker: check IP and firewall)");
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(RAIN_PWR, OUTPUT);
  dht.begin();
  connectWifi();
  mqtt.setServer(mqtt_server, 1883);
  mqtt.setSocketTimeout(5);  
}
// check dht11 
void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();
//read dht11 if i have hardware, but now i have it so this is for explanation =)
  if (mqtt.connected() && millis() - lastSend >= 20000) {
    lastSend = millis();
    float t = HAS_DHT11 ? dht.readTemperature() : 0;
    float h = HAS_DHT11 ? dht.readHumidity() : 0;
    int rain = readRainPct();

    if (HAS_DHT11 && (isnan(t) || isnan(h))) {
      Serial.println("DHT11 read failed, skipping this reading");
    } else {
//pack the data into json payload
      char payload[80];
      snprintf(payload, sizeof(payload),
               "{\"t\":%.1f,\"h\":%.0f,\"rain\":%d}", t, h, rain);
//push payload to mqtt
      bool ok = mqtt.publish(topic, payload);
//log
      Serial.print(payload);
      Serial.println(ok ? "  [sent]" : "  [publish FAILED]");
    }
  }
}
