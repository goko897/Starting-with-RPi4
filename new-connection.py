# -- coding: utf-8 --
import time
import ssl
import os
import random
import datetime
import json
import numpy as np
import cv2
import board
import adafruit_dht
import pytesseract
import paho.mqtt.client as mqtt

# MQTT Configuration
MQTT_BROKER = "192.168.47.115"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "rpi_sever"

# MQTT Topics
PUB_TOPIC = "org.eclipse.ditto/your-device-path/things/live/messages"

# DHT Sensor Configuration - Updated for adafruit_dht
dht_device = adafruit_dht.DHT11(board.D4)

# OCR Configuration
plateCascade = cv2.CascadeClassifier("/home/rpi/Desktop/ocr/haarcascade_russian_plate_number.xml")
minArea = 1500  # Minimum area for detecting number plates

# Paths
images_folder = "/home/rpi/Desktop/ocr/Dataset"
detected_plates_folder = "/home/rpi/Desktop/ocr/Detected_Images"

if not os.path.exists(detected_plates_folder):
    os.makedirs(detected_plates_folder)

count = 0  # Counter for saved plates

# State codes mapping for OCR
states = {
    "AN": "Andaman and Nicobar Islands", "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh",
    "AS": "Assam", "BR": "Bihar", "CG": "Chhattisgarh", "CH": "Chandigarh",
    "DD": "Daman and Diu", "DL": "Delhi", "GA": "Goa", "GJ": "Gujarat",
    "HR": "Haryana", "HP": "Himachal Pradesh", "JH": "Jharkhand",
    "JK": "Jammu and Kashmir", "KA": "Karnataka", "KL": "Kerala",
    "LD": "Lakshadweep", "MH": "Maharashtra", "MN": "Manipur",
    "MP": "Madhya Pradesh", "MZ": "Mizoram", "NL": "Nagaland",
    "OR": "Odisha", "PB": "Punjab", "PY": "Puducherry",
    "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu",
    "TR": "Tripura", "TS": "Telangana", "UK": "Uttarakhand",
    "UP": "Uttar Pradesh", "WB": "West Bengal"
}

# Setup MQTT Client
def setup_mqtt_client():
    mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
    
    mqtt_client.connect(MQTT_BROKER, port=MQTT_PORT)
    mqtt_client.loop_start()
    print("Connected to the HiveMQ Broker")
    return mqtt_client

# Updated DHT sensor read function based on the provided example
def read_dht_sensor():
    try:
        # Read temperature and humidity directly from the dht_device object
        temperature = dht_device.temperature
        humidity = dht_device.humidity
        
        # Convert to float to avoid TypeErrors
        temperature = float(temperature) if temperature is not None else 0.0
        humidity = float(humidity) if humidity is not None else 0.0
        
        return temperature, humidity
    
    except RuntimeError as e:
        # Handle sensor read errors
        print(f"Error reading DHT sensor: {e}")
        return 0.0, 0.0  # Return default values to prevent crashes
    except Exception as e:
        print(f"Unexpected error reading DHT sensor: {e}")
        return 0.0, 0.0

# Publish sensor data in structured JSON format
def publish_sensor_reading(mqtt_client, temperature, humidity, numberplate, number, state, time_stamp):
    # Convert sensor readings to appropriate values
    temperature_value = float(temperature) if temperature is not None else 0.0
    humidity_value = float(humidity) if humidity is not None else 0.0

    # Prepare the compressed payload format like ESP32
    data = {
        "temp": temperature_value,
        "gaz": humidity_value,
        "alert": 1 if numberplate else 0,  # Alert LED turns on if a plate is detected
        "thingId": "sensor.test:hivelab",
        "plate_data": {
            "numberplate": numberplate if numberplate else "N/A",
            "number": number if number else 0,
            "state": state if state else "Unknown",
            "time": time_stamp if time_stamp else "N/A"
        }
    }

    # Publish the JSON payload to the MQTT broker
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
                cv2.rectangle(img_original, (x, y), (x+w, y+h), (255, 0, 0), 2)
                imgRoi = img[y:y + h, x:x + w]

                imgRoiGray = cv2.cvtColor(imgRoi, cv2.COLOR_BGR2GRAY)
                _, imgRoiThresh = cv2.threshold(imgRoiGray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                imgRoiThresh = cv2.dilate(imgRoiThresh, kernel, iterations=1)

                read = pytesseract.image_to_string(imgRoiThresh, config='--psm 6')
                read = "".join([c for c in read if c.isalnum() or c.isspace()]).strip()

                if read:
                    state_code = read[:2].upper()
                    state_name = states.get(state_code, "Unknown")
                    now = datetime.datetime.now()
                    date_time = now.strftime('%Y-%m-%d %H:%M')

                    print(f"Detected Plate: {read} | State: {state_name} | Time: {date_time}")

                    save_file = os.path.join(detected_plates_folder, f"plate_{count}.jpg")
                    cv2.imwrite(save_file, imgRoiThresh)
                    count += 1

                    return read, len(read), state_name, date_time

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
        # Clean up
        dht_device.exit()  # Properly close the DHT device
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Disconnected from the MQTT broker")

if __name__ == "__main__":
    main()
