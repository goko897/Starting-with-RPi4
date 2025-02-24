# -- coding: utf-8 --
import time
import ssl
import os
import random
import datetime
import json
import numpy as np
import cv2
import adafruit_dht as Adafruit_DHT
import pytesseract
import paho.mqtt.client as mqtt

# ⬇️ UPDATE THIS with your laptop's local IP (Use `ipconfig` or `ifconfig/ip a`)
MQTT_BROKER = "192.168.47.115"  # Replace with your laptop's local IP
MQTT_PORT = 1883  # Standard MQTT port for local brokers
MQTT_CLIENT_ID = "rpi_sensor_client"

# MQTT Topics
PUB_TOPIC = "topic/sensors"

# DHT Sensor Configuration
DHT_SENSOR = Adafruit_DHT.DHT11  # Use DHT22 if applicable
DHT_PIN = 4  # GPIO pin where the DHT sensor is connected

# OCR Configuration
plateCascade = cv2.CascadeClassifier("/home/rpi/Desktop/ocr/haarcascade_russian_plate_number.xml")
minArea = 1500  # Minimum area for detecting number plates

# Paths
images_folder = "/home/rpi/Desktop/ocr/Dataset"
detected_plates_folder = "/home/rpi/Desktop/ocr/Detected_Images"

if not os.path.exists(detected_plates_folder):
    os.makedirs(detected_plates_folder)

count = 0  # Counter for saved plates

# Setup MQTT Client (Local Broker)
def setup_mqtt_client():
    mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)  # Use v3.1.1 for local brokers
    mqtt_client.connect(MQTT_BROKER, port=MQTT_PORT)  # No username/password needed for local connection
    mqtt_client.loop_start()
    print(f"Connected to local MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    return mqtt_client

# Read DHT sensor data
def read_dht_sensor():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    return temperature, humidity

# Publish sensor data in structured JSON format
def publish_sensor_reading(mqtt_client, temperature, humidity, numberplate, number, state, time_stamp):
    data = {
        "thingId": "sensor.test:hivelab",
        "policyId": "my.test:policy",
        "features": {
            "sensor01": {
                "properties": {
                    "temperature": temperature if temperature is not None else 0,
                    "humidity": humidity if humidity is not None else 0
                }
            },
            "sensor02": {
                "properties": {
                    "numberplate": numberplate,
                    "number": number,
                    "state": state,
                    "time": time_stamp
                }
            }
        }
    }

    mqtt_client.publish(PUB_TOPIC, json.dumps(data))
    print(f"Published to {PUB_TOPIC}: {json.dumps(data, indent=4)}")

# Process Image for OCR
def detect_license_plate():
    global count

    image_files = [f for f in os.listdir(images_folder) if os.path.isfile(os.path.join(images_folder, f))]
    if not image_files:
        print("No images found in the folder.")
        return None, None, None, None

    image_path = os.path.join(images_folder, random.choice(image_files))
    print(f"Processing image: {image_path}")

    try:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Image {image_path} not found or could not be loaded.")

        img_original = img.copy()
        img = cv2.resize(img, (800, 600))
        imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        kernel = np.ones((3, 3), np.uint8)
        imgGray = cv2.morphologyEx(imgGray, cv2.MORPH_CLOSE, kernel)
        imgGray = cv2.equalizeHist(imgGray)
        imgGray = cv2.GaussianBlur(imgGray, (5, 5), 0)

        _, imgThresh = cv2.threshold(imgGray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        numberPlates = plateCascade.detectMultiScale(imgGray, 1.1, 4)

        for (x, y, w, h) in numberPlates:
            area = w * h
            if area > minArea:
                cv2.rectangle(img_original, (x, y, w, h), (255, 0, 0), 2)
                imgRoi = img[y:y + h, x:x + w]

                imgRoiGray = cv2.cvtColor(imgRoi, cv2.COLOR_BGR2GRAY)
                _, imgRoiThresh = cv2.threshold(imgRoiGray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                imgRoiThresh = cv2.dilate(imgRoiThresh, kernel, iterations=1)

                read = pytesseract.image_to_string(imgRoiThresh, config='--psm 6')
                read = "".join([c for c in read if c.isalnum() or c.isspace()]).strip()

                if read:
                    now = datetime.datetime.now()
                    date_time = now.strftime('%Y-%m-%d %H:%M')

                    print(f"Detected Plate: {read} | Time: {date_time}")

                    save_file = os.path.join(detected_plates_folder, f"plate_{count}.jpg")
                    cv2.imwrite(save_file, imgRoiThresh)
                    count += 1

                    return read, len(read), "Unknown", date_time

        return None, None, None, None

    except Exception as e:
        print(f"Error processing image: {e}")
        return None, None, None, None

# Main Function
def main():
    mqtt_client = setup_mqtt_client()

    try:
        print("Monitoring temperature, humidity, and detecting license plates. Press CTRL+C to exit.")

        while True:
            temperature, humidity = read_dht_sensor()
            numberplate, number, state, time_stamp = detect_license_plate()
            
            publish_sensor_reading(mqtt_client, temperature, humidity, numberplate, number, state, time_stamp)
            time.sleep(5)

    except KeyboardInterrupt:
        print("Stopping the program")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Disconnected from the MQTT broker")

if __name__ == "__main__":
    main()
