import json
import os
import time

import paho.mqtt.client as mqtt
import requests

NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
NTFY_TOKEN = os.getenv("NTFY_TOKEN", "")
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
TOPIC = os.getenv("MQTT_TOPIC", "weather/data")
TEMP_HIGH = float(os.getenv("TEMP_HIGH", "35"))
HUM_HIGH = float(os.getenv("HUM_HIGH", "90"))
RAIN_ON = int(os.getenv("RAIN_ON", "30"))
COOLDOWN = int(os.getenv("ALERT_COOLDOWN", "1800"))
OFFLINE_AFTER = int(os.getenv("OFFLINE_AFTER", "180"))
THINGSPEAK_KEY = os.getenv("THINGSPEAK_API_KEY", "")

last_seen = 0.0
raining = False
offline_notified = False
last_alert = {}
last_thingspeak = 0.0


def send(text, title="Weather station", priority="default", tags=""):
    headers = {"Title": title, "Priority": priority}
    if tags:
        headers["Tags"] = tags
    if NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {NTFY_TOKEN}"
    try:
        requests.post(f"{NTFY_SERVER}/{NTFY_TOPIC}",
                      data=text.encode("utf-8"), headers=headers, timeout=10)
    except requests.RequestException as e:
        print("ntfy error:", e)


def alert(key, text, **kw):
    now = time.time()
    if now - last_alert.get(key, 0) >= COOLDOWN:
        last_alert[key] = now
        send(text, **kw)


def push_thingspeak(t, h, rain):
    global last_thingspeak
    if not THINGSPEAK_KEY or time.time() - last_thingspeak < 16:
        return
    last_thingspeak = time.time()
    try:
        requests.get("https://api.thingspeak.com/update",
                     params={"api_key": THINGSPEAK_KEY,
                             "field1": t, "field2": h, "field3": rain},
                     timeout=10)
    except requests.RequestException as e:
        print("ThingSpeak error:", e)


def on_message(client, userdata, msg):
    global last_seen, raining, offline_notified
    try:
        d = json.loads(msg.payload)
        t, h, rain = float(d["t"]), float(d["h"]), int(d["rain"])
    except (ValueError, KeyError):
        return
    last_seen = time.time()
    push_thingspeak(t, h, rain)
    if offline_notified:
        offline_notified = False
        send("Station is back online.", tags="white_check_mark")

    if rain >= RAIN_ON and not raining:
        raining = True
        send(f"Rain detected ({rain}% wetness).",
             title="Rain alert", priority="high", tags="umbrella")
    elif rain < RAIN_ON // 2 and raining:
        raining = False
        send("Rain has stopped.", title="Rain stopped", priority="low",
             tags="sunny")

    if t >= TEMP_HIGH:
        alert("temp", f"High temperature: {t:.1f} C",
              title="Heat alert", priority="high", tags="thermometer")
    if h >= HUM_HIGH:
        alert("hum", f"High humidity: {h:.0f}%",
              title="Humidity alert", tags="droplet")


def on_connect(client, userdata, flags, reason_code, properties):
    print("MQTT connected:", reason_code)
    client.subscribe(TOPIC)


def main():
    global offline_notified
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    while True:
        try:
            client.connect(MQTT_HOST, 1883, 60)
            break
        except OSError:
            print("Waiting for broker...")
            time.sleep(3)
    client.loop_start()
    send("Alert service started.", tags="rocket")
    while True:
        time.sleep(15)
        if (last_seen and not offline_notified
                and time.time() - last_seen > OFFLINE_AFTER):
            offline_notified = True
            send("No data received from the station.",
                 title="Station offline", priority="urgent",
                 tags="rotating_light")


if __name__ == "__main__":
    main()
