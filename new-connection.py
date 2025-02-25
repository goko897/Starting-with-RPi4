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
MQTT_BROKER = "192.168.47.115"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "rpi_server"  # Fixed typo in client ID
MQTT_USERNAME = None  # Add if your broker requires authentication
MQTT_PASSWORD = None  # Add if your broker requires authentication

# MQTT Topics - Updated based on error message
# Changed to match the expected format in the HiveMQ connection configuration
PUB_TOPIC = "devices/sensor.test:hivelab"  # Changed from "topic/sensors" to match enforcement filters

# DHT Sensor Configuration
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

# MQTT Callback functions for debugging
def on_connect(client, userdata, flags, rc):
    connection_responses = {
        0: "Connection successful",
        1: "Connection refused - incorrect protocol version",
        2: "Connection refused - invalid client identifier",
        3: "Connection refused - server unavailable",
        4: "Connection refused - bad username or password",
        5: "Connection refused - not authorized"
    }
    response = connection_responses.get(rc, f"Unknown response code: {rc}")
    logger.info(f"Connected to MQTT Broker with result code: {rc} - {response}")
    
def on_disconnect(client, userdata, rc):
    logger.warning(f"Disconnected from MQTT Broker with result code: {rc}")

def on_publish(client, userdata, mid):
    logger.debug(f"Message {mid} published successfully")

def on_log(client, userdata, level, buf):
    logger.debug(f"MQTT Log: {buf}")

# Setup MQTT Client with enhanced error handling
def setup_mqtt_client():
    mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
    
    # Set up callback functions
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_publish = on_publish
    mqtt_client.on_log = on_log
    
    # Add authentication if needed
    if MQTT_USERNAME and MQTT_PASSWORD:
        mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    try:
        logger.info(f"Connecting to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}")
        mqtt_client.connect(MQTT_BROKER, port=MQTT_PORT)
        mqtt_client.loop_start()
        logger.info("Connected to the HiveMQ Broker")
        return mqtt_client
    except Exception as e:
        logger.error(f"Failed to connect to MQTT Broker: {e}")
        raise

# Updated DHT sensor read function
def read_dht_sensor():
    try:
        temperature = dht_device.temperature
        humidity = dht_device.humidity
        
        temperature = float(temperature) if temperature is not None else 0.0
        humidity = float(humidity) if humidity is not None else 0.0
        
        logger.debug(f"DHT Sensor reading: Temperature={temperature}°C, Humidity={humidity}%")
        return temperature, humidity
    
    except RuntimeError as e:
        logger.warning(f"Error reading DHT sensor: {e}")
        return 0.0, 0.0
    except Exception as e:
        logger.error(f"Unexpected error reading DHT sensor: {e}")
        return 0.0, 0.0

# Publish sensor data in structured JSON format - Updated to match expected format in mapping
def publish_sensor_reading(mqtt_client, temperature, humidity, numberplate, number, state, time_stamp):
    # Updated payload format to match the expected structure in your JavaScript mapping function
    data = {
        "temperature": float(temperature) if temperature is not None else 0.0,
        "humidity": float(humidity) if humidity is not None else 0.0,
        "numberplate": numberplate if numberplate else "N/A",
        "number": number if number else 0,
        "state": state if state else "Unknown",
        "time": time_stamp if time_stamp else "N/A",
        "thingId": "sensor.test:hivelab"
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
    
# Process Image for OCR
def detect_license_plate():
    global count

    image_files = [f for f in os.listdir(images_folder) if os.path.isfile(os.path.join(images_folder, f))]
    if not image_files:
        logger.warning("No images found in the folder.")
        return None, None, None, None

    image_path = os.path.join(images_folder, random.choice(image_files))
    logger.info(f"Processing image: {image_path}")

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

                    logger.info(f"Detected Plate: {read} | State: {state_name} | Time: {date_time}")

                    save_file = os.path.join(detected_plates_folder, f"plate_{count}.jpg")
                    cv2.imwrite(save_file, imgRoiThresh)
                    count += 1

                    return read, len(read), state_name, date_time

        logger.info("No license plates detected in the image.")
        return None, None, None, None

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return None, None, None, None

# Main Function
def main():
    try:
        mqtt_client = setup_mqtt_client()
        logger.info("Monitoring temperature, humidity, and detecting license plates. Press CTRL+C to exit.")

        while True:
            try:
                temperature, humidity = read_dht_sensor()
                numberplate, number, state, time_stamp = detect_license_plate()
                
                publish_sensor_reading(mqtt_client, temperature, humidity, numberplate, number, state, time_stamp)
                
                # Sleep with error handling in case of keyboard interrupt
                time.sleep(5)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)  # Continue with next iteration after error

    except KeyboardInterrupt:
        logger.info("Stopping the program due to keyboard interrupt")
    except Exception as e:
        logger.critical(f"Critical error in main function: {e}")
    finally:
        try:
            # Clean up
            dht_device.exit()  # Properly close the DHT device
            logger.info("DHT device closed")
        except Exception as e:
            logger.error(f"Error closing DHT device: {e}")
            
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            logger.info("Disconnected from the MQTT broker")
        except Exception as e:
            logger.error(f"Error disconnecting from MQTT broker: {e}")

if __name__ == "__main__":
    main()
