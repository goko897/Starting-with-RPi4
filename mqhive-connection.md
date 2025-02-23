```
# -- coding: utf-8 --
import time
import ssl
import board
import adafruit_dht
import paho.mqtt.client as mqtt
import cv2
import pytesseract

# MQTT Configuration
MQTT_BROKER = "054a692930274fb1a433891ca5b5d023.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_CLIENT_ID = "pico"
MQTT_USER = "Priyanshu08"
MQTT_PASSWORD = "Allsmall88"

# Topics for publishing data
pub_topic_temperature = "topic/sensors/temperature"
pub_topic_humidity = "topic/sensors/humidity"
pub_topic_ocr = "topic/sensors/ocr"

# DHT11 Sensor Configuration
DHT_PIN = 4  # GPIO pin for DHT11 sensor
dht_device = adafruit_dht.DHT11(board.D4, use_pulseio=False)

def setup_mqtt_client():
    mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv5)
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqtt_client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                         cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS, ciphers=None)
    mqtt_client.connect(MQTT_BROKER, port=MQTT_PORT)
    mqtt_client.loop_start()
    print("Connected to HiveMQ Broker")
    return mqtt_client

def read_temperature_humidity():
    try:
        temperature_c = dht_device.temperature
        humidity = dht_device.humidity
        return temperature_c, humidity
    except RuntimeError:
        return None, None

def perform_ocr(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    # OCR Processing
    text = pytesseract.image_to_string(thresh, config='--psm 8')
    return text.strip()

def publish_sensor_reading(mqtt_client, topic, message):
    mqtt_client.publish(topic, message)
    print(f"Published to {topic}: {message}")

def main():
    mqtt_client = setup_mqtt_client()

    try:
        print("Monitoring DHT11 sensor & performing OCR. Press CTRL+C to exit.")

        while True:
            # Read Temperature & Humidity
            temperature_c, humidity = read_temperature_humidity()

            if temperature_c is not None and humidity is not None:
                publish_sensor_reading(mqtt_client, pub_topic_temperature, f"{temperature_c:.2f}°C")
                publish_sensor_reading(mqtt_client, pub_topic_humidity, f"{humidity:.2f}%")

            # OCR Processing
            ocr_text = perform_ocr("plate.jpg")  # Replace with your image path
            if ocr_text:
                publish_sensor_reading(mqtt_client, pub_topic_ocr, f"Plate: {ocr_text}")

            time.sleep(2)

    except KeyboardInterrupt:
        print("Stopping program")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Disconnected from MQTT")

if __name__ == "__main__":
    main()

```

## Setup & Run
1. Install dependencies
```
pip install paho-mqtt adafruit-circuitpython-dht opencv-python pytesseract
sudo apt-get install tesseract-ocr libtesseract-dev
```
2. Save an image named plate.jpg in the same directory.
```
python3 script.py
```
3. View MQTT messages in HiveMQ.
