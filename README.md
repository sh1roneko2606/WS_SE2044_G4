# Weather Station Docker Stack

This project builds a small IoT weather monitoring system using a NodeMCU board with a DHT11 temperature/humidity sensor and a rain sensor. The device publishes readings over MQTT, and a Docker-based stack stores, visualizes, and alerts on the incoming data.

## Architecture

```text
NodeMCU sensor node
        │
        ▼
MQTT broker (Mosquitto)
        │
   ┌────┼────┐
   │    │    │
   ▼    ▼    ▼
Dashboard  Alert bot  Optional simulator
```

The system includes:
- a NodeMCU sketch that reads sensor values and publishes them to MQTT
- a Mosquitto broker for message transport
- a Flask dashboard for live readings and recent history
- an alert service that pushes notifications via ntfy
- optional ThingSpeak integration for cloud uploads
- a simulator to test the system without hardware

## Features

- Real-time weather data visualization
- Temperature, humidity, and rain status monitoring
- Offline status detection
- ntfy notifications for rain, heat, humidity, and offline conditions
- Historical trend charting in the dashboard
- Dockerized deployment for easy setup
- Hardware-independent simulator mode for testing

## Prerequisites

Before running the project, make sure you have:
- Docker Engine + Docker Compose
- A networked machine (Linux/macOS/Windows with Docker) where the stack will run
- A NodeMCU board, DHT11 sensor, and rain sensor if using real hardware
- Optional: an Arduino/ESP8266 toolchain to flash the board

## Quick Start

1. Copy the sample environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and set the required values. At minimum:
- `NTFY_TOPIC` for your ntfy topic
- `MQTT_TOPIC` if you want a non-default MQTT topic
- leave `THINGSPEAK_API_KEY` empty if you do not want to push data to ThingSpeak

3. Start the stack:

```bash
docker compose up -d --build
```

4. Open the dashboard in your browser:

```text
http://<docker-host-ip>:8080
```

## Environment Variables

The stack uses variables from `.env` and defaults from `.env.example`.

| Variable | Purpose | Default |
|---|---|---|
| `NTFY_TOPIC` | ntfy channel used for alerts | `YOUR_NTFY_TOPIC` |
| `NTFY_SERVER` | ntfy server URL | `https://ntfy.sh` |
| `NTFY_TOKEN` | optional authentication token | `YOUR_NTFY_TOKEN` |
| `MQTT_HOST` | MQTT broker hostname | `mosquitto` |
| `MQTT_TOPIC` | topic for sensor messages | `weather/data` |
| `TEMP_HIGH` | high temperature alert threshold | `35` |
| `HUM_HIGH` | high humidity alert threshold | `90` |
| `RAIN_ON` | rain intensity threshold | `30` |
| `ALERT_COOLDOWN` | cooldown between repeated alerts | `1800` |
| `OFFLINE_AFTER` | time before station is marked offline | `180` |
| `THINGSPEAK_API_KEY` | ThingSpeak API key | `YOUR_THINGSPEAK_API_KEY` |
| `SIM_INTERVAL` | simulator publish interval | `5` |

## Flashing the NodeMCU

Open the Arduino sketch in:

```text
nodemcu/ws_src.ino
```

Update the following before uploading:
- Wi-Fi SSID
- Wi-Fi password
- MQTT broker address (`mqtt_server`)

Use the Docker host's LAN IP address as the broker address when running the stack on the same local network.

Example:

```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "192.168.1.25";
```

Then flash the board through the Arduino IDE or your preferred ESP8266 toolchain.

## Testing the System

### Publish a test message manually

```bash
docker compose exec mosquitto mosquitto_pub -t weather/data -m '{"t":28.5,"h":70,"rain":0}'
```

This validates that the MQTT broker and dashboard are accepting data.

### Run the simulator (no hardware needed)

```bash
docker compose --profile sim up -d simulator
```

To watch simulator output:

```bash
docker compose logs -f simulator
```

To stop it:

```bash
docker compose stop simulator
```

## Project Structure

```text
weather-station-docker/
├── .env.example
├── .env
├── docker-compose.yml
├── README.md
├── bot/
│   ├── bot.py
│   ├── Dockerfile
│   └── requirements.txt
├── dashboard/
│   ├── app.py
│   ├── static/
│   ├── Dockerfile
│   └── requirements.txt
├── mosquitto/
│   └── mosquitto.conf
├── nodemcu/
│   └── ws_src.ino
├── simulator/
│   └── simulate.py
└── .gitignore
```

## Notes

- The dashboard is served on port `8080`.
- MQTT listens on port `1883` internally and externally for local testing.
- The alert bot sends notifications through ntfy, so you should keep the topic name and credentials aligned with your ntfy setup.
- If you do not use ThingSpeak, leave the API key blank to disable uploads.

## License

This project is intended for coursework / local development use and is not published under a formal license unless your course or team adds one.
