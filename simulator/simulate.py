"""Fake NodeMCU: publishes the same JSON the real sketch sends.

Cycle (repeats): normal -> rain -> clearing -> hot & humid
Run on the host:   python simulate.py
Run with Docker:   docker compose --profile sim up simulator
"""
import json
import os
import random
import time

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "localhost")
TOPIC = os.getenv("MQTT_TOPIC", "weather/data")
INTERVAL = float(os.getenv("SIM_INTERVAL", "5"))   # seconds between readings

# (name, seconds)
PHASES = [("normal", 40), ("rain", 50), ("clearing", 25), ("hot", 40)]
CYCLE = sum(d for _, d in PHASES)


def phase_at(elapsed):
    e = elapsed % CYCLE
    for name, dur in PHASES:
        if e < dur:
            return name, e / dur
        e -= dur
    return PHASES[-1][0], 1.0


def reading(elapsed):
    name, p = phase_at(elapsed)
    n = lambda s: random.uniform(-s, s)
    if name == "normal":
        t, h, rain = 27 + n(0.3), 65 + n(2), 0
    elif name == "rain":
        t, h, rain = 24 + n(0.3), 88 + n(2), min(95, 40 + 60 * p) + n(3)
    elif name == "clearing":
        t, h, rain = 26 + n(0.3), 80 - 10 * p + n(2), 40 * (1 - p) + n(1)
    else:  # hot
        t, h, rain = 36.5 + n(0.5), 92 + n(2), 0
    rain = max(0, min(100, rain))
    return name, {"t": round(t, 1), "h": round(max(0, min(100, h))),
                  "rain": int(rain)}


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    while True:
        try:
            client.connect(HOST, 1883, 60)
            break
        except OSError:
            print("Waiting for broker at", HOST)
            time.sleep(3)
    client.loop_start()
    start = time.time()
    print(f"Simulating a station every {INTERVAL}s -> {HOST}/{TOPIC}")
    while True:
        name, data = reading(time.time() - start)
        client.publish(TOPIC, json.dumps(data, separators=(",", ":")))
        print(f"[{name:8}] {data}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
