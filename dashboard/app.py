import json
import os
import sqlite3
import threading
import time

import paho.mqtt.client as mqtt
from flask import Flask, jsonify, request, send_from_directory

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
TOPIC = os.getenv("MQTT_TOPIC", "weather/data")
DB_PATH = os.getenv("DB_PATH", "/data/readings.db")
OFFLINE_AFTER = int(os.getenv("OFFLINE_AFTER", "180"))
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))

app = Flask(__name__, static_folder="static", static_url_path="/static")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute("PRAGMA journal_mode=WAL")
db.execute("CREATE TABLE IF NOT EXISTS readings "
           "(ts INTEGER PRIMARY KEY, t REAL, h REAL, rain INTEGER)")
db.commit()

lock = threading.Lock()
latest = None
last_cleanup = 0


def load_latest():
    global latest
    with lock:
        row = db.execute(
            "SELECT ts, t, h, rain FROM readings ORDER BY ts DESC LIMIT 1"
        ).fetchone()
    if row:
        latest = {"ts": row[0], "t": row[1], "h": row[2], "rain": row[3]}


def store(t, h, rain):
    global latest, last_cleanup
    ts = int(time.time())
    with lock:
        db.execute("INSERT OR REPLACE INTO readings VALUES (?, ?, ?, ?)",
                   (ts, t, h, rain))
        if ts - last_cleanup > 3600:
            last_cleanup = ts
            db.execute("DELETE FROM readings WHERE ts < ?",
                       (ts - RETENTION_DAYS * 86400,))
        db.commit()
    latest = {"ts": ts, "t": t, "h": h, "rain": rain}


def on_connect(client, userdata, flags, reason_code, properties):
    print("MQTT connected:", reason_code)
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    try:
        d = json.loads(msg.payload)
        store(float(d["t"]), float(d["h"]), int(d["rain"]))
    except (ValueError, KeyError, TypeError):
        pass


def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    def run():
        while True:
            try:
                client.connect(MQTT_HOST, 1883, 60)
                break
            except OSError:
                print("Waiting for broker...")
                time.sleep(3)
        client.loop_forever()   # reconnects automatically

    threading.Thread(target=run, daemon=True).start()


def rain_status(pct):
    return "Dry" if pct < 10 else "Light rain" if pct < 50 else "Heavy rain"


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/latest")
def api_latest():
    d = latest
    if not d:
        return jsonify(has_data=False)
    age = int(time.time()) - d["ts"]
    return jsonify(has_data=True, **d, age=age,
                   online=age <= OFFLINE_AFTER, status=rain_status(d["rain"]))


@app.get("/api/history")
def api_history():
    try:
        hours = float(request.args.get("hours", "6"))
    except ValueError:
        hours = 6.0
    hours = min(max(hours, 0.25), RETENTION_DAYS * 24)
    since = int(time.time()) - int(hours * 3600)
    bucket = max(1, int(hours * 3600) // 300)   # about 300 points per chart
    with lock:
        rows = db.execute(
            "SELECT (ts / ?) * ? AS b, AVG(t), AVG(h), AVG(rain) "
            "FROM readings WHERE ts >= ? GROUP BY b ORDER BY b",
            (bucket, bucket, since)).fetchall()
    points = [[r[0], round(r[1], 1), round(r[2], 1), round(r[3], 1)]
              for r in rows]
    return jsonify(hours=hours, points=points)


load_latest()
start_mqtt()
