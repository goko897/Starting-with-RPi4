import time
import ssl
import os
import random
import datetime
import json
import base64
import numpy as np
import cv2
import board
import adafruit_dht
import pytesseract
import paho.mqtt.client as mqtt
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/home/rpi/Desktop/ocr/mqtt_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RPI_MQTT")

# MQTT Configuration
MQTT_BROKER = "192.168.229.115"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "rpi_server"
PUB_TOPIC = "devices/sensor.test:hivelab/messages"

# DHT Sensor Configuration
dht_device = adafruit_dht.DHT11(board.D4)

# Paths
images_folder = "/home/rpi/Desktop/ocr/Dataset"
detected_plates_folder = "/home/rpi/Desktop/ocr/Detected_Images"
bin_file_path = "/home/rpi/Desktop/ocr/data.bin"  # Path to the .bin file

if not os.path.exists(detected_plates_folder):
    os.makedirs(detected_plates_folder)

def setup_mqtt_client():
    mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
    mqtt_client.connect(MQTT_BROKER, port=MQTT_PORT)
    mqtt_client.loop_start()
    print("Connected to the MQTT Broker")
    return mqtt_client

def read_dht_sensor():
    try:
        temperature = float(dht_device.temperature or 0.0)
        humidity = float(dht_device.humidity or 0.0)
        return temperature, humidity
    except Exception as e:
        logger.error(f"Error reading DHT sensor: {e}")
        return 0.0, 0.0

def read_bin_file():
    try:
        with open(bin_file_path, "rb") as file:
            return base64.b64encode(file.read()).decode()
    except Exception as e:
        logger.error(f"Error reading .bin file: {e}")
        return ""

def publish_sensor_reading(mqtt_client, temperature, humidity, numberplate, number, state, time_stamp, bin_data):
    data = {
        "temperature": temperature,
        "humidity": humidity,
        "numberplate": numberplate or "N/A",
        "number": number or 0,
        "state": state or "Unknown",
        "time": time_stamp or "N/A",
        "thingId": "sensor.test:hivelab",
        "bin_file": bin_data  # Send .bin file as Base64 string
    }
    
    try:
        payload = json.dumps(data)
        result = mqtt_client.publish(PUB_TOPIC, payload, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Published to {PUB_TOPIC}: {payload}")
        else:
            logger.error(f"Failed to publish message, error code: {result.rc}")
    except Exception as e:
        logger.error(f"Error publishing message: {e}")

def main():
    mqtt_client = setup_mqtt_client()

    try:
        print("Monitoring sensors and uploading data. Press CTRL+C to exit.")
        while True:
            temperature, humidity = read_dht_sensor()
            bin_data = read_bin_file()
            numberplate, number, state, time_stamp = None, None, None, None  # Modify with actual plate detection
            publish_sensor_reading(mqtt_client, temperature, humidity, numberplate, number, state, time_stamp, bin_data)
            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopping the program")
    finally:
        dht_device.exit()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Disconnected from the MQTT broker")

if __name__ == "__main__":
    main()
