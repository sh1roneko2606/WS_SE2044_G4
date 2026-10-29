# IoT weather station

NodeMCU (DHT11 + rain sensor) -> MQTT -> Docker stack (Mosquitto, dashboard, alert service)

## Run
    cp .env.example .env      # set NTFY_TOPIC (leave THINGSPEAK_API_KEY empty if unused)
    docker compose up -d --build

## Open the dashboard
    http://<docker-host-ip>:8080

## Flash the NodeMCU
Open nodemcu/weather_station.ino, set ssid, pass and mqtt_server (the Docker host's LAN IP).

## Test without hardware
    docker compose exec mosquitto mosquitto_pub -t weather/data -m '{"t":28.5,"h":70,"rain":0}'

## Test with the simulator (no hardware)
    docker compose --profile sim up -d simulator
    docker compose logs -f simulator
Stop it with `docker compose stop simulator`.
