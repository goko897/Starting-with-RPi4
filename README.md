# Starting-with-RPi4

## python 
```sudo apt-get install build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev ```

https://www.enablegeek.com/tutorial/install-python-on-a-raspberry-pi-step-by-step-guide/#:~:text=Downloading%20Python,-The%20next%20step&text=Open%20a%20web%20browser%20on,0.


[DHT 11 Sensor] [!https://www.electronicwings.com/raspberry-pi/dht11-interfacing-with-raspberry-pi]              

1. Create a virtual environment (replace myenv with any name you prefer):
```python3 -m venv myenv ```

2.Activate the virtual environment:
```source myenv/bin/activate```

3.Install the required library inside the virtual environment:
```pip3 install adafruit-circuitpython-dht```

4.Run your Python script within the virtual environment.

simpletest_dht.py
```
# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_dht

# Initial the dht device, with data pin connected to:
dhtDevice = adafruit_dht.DHT22(board.D18)

# you can pass DHT22 use_pulseio=False if you wouldn't like to use pulseio.
# This may be necessary on a Linux single board computer like the Raspberry Pi,
# but it will not work in CircuitPython.
# dhtDevice = adafruit_dht.DHT22(board.D18, use_pulseio=False)

while True:
    try:
        # Print the values to the serial port
        temperature_c = dhtDevice.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = dhtDevice.humidity
        print(
            "Temp: {:.1f} F / {:.1f} C    Humidity: {}% ".format(
                temperature_f, temperature_c, humidity
            )
        )

    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        print(error.args[0])
        time.sleep(2.0)
        continue
    except Exception as error:
        dhtDevice.exit()
        raise error

    time.sleep(2.0)

```

```
import time
import board
import adafruit_dht

# Initialize the DHT11 sensor connected to GPIO4
dht_device = adafruit_dht.DHT11(board.D4)

while True:
    try:
        # Read temperature and humidity from the sensor
        temperature = dht_device.temperature
        humidity = dht_device.humidity

        if temperature is not None and humidity is not None:
            print(f"Temp: {temperature:.1f}°C  Humidity: {humidity:.1f}%")
        else:
            print("Failed to retrieve data from sensor. Trying again...")

    except RuntimeError as error:
        # Error handling for common issues like checksum errors
        print(f"Sensor error: {error}. Retrying...")

    except Exception as error:
        dht_device.exit()
        raise error

    # Wait before trying again
    time.sleep(2)

```




# Steps to Integrate:
Ensure Raspberry Pi 4 is set up with MQTT

Install necessary dependencies on the Pi:
bash
Copy
Edit
sudo apt update
sudo apt install python3-opencv tesseract-ocr libtesseract-dev
pip install paho-mqtt adafruit-circuitpython-dht
Ensure tesseract-ocr is installed and set the correct path in your script.
Modify the Number Plate Detection Code

Integrate MQTT to send the detected plate number.
Remove infinite looping in the script to process one image at a time.
Modify MQTT Script

Add a function to capture and process images using OpenCV.
Send the OCR result to MQTT.
Updated Combined Code
python
Copy
Edit
import cv2
import pytesseract
import os
import numpy as np
import datetime
import time
import ssl
import board
import adafruit_dht
import paho.mqtt.client as mqtt

# Set Tesseract path (modify for Raspberry Pi)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # For Linux (Pi)

# Haar Cascade path
plateCascade = cv2.CascadeClassifier('/home/pi/haarcascade_russian_plate_number.xml')

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
DHT_PIN = board.D4
dht_device = adafruit_dht.DHT11(DHT_PIN, use_pulseio=False)

# Image Processing Paths
images_folder = "/home/pi/images"
detected_plates_folder = "/home/pi/Detected_Plates"
os.makedirs(detected_plates_folder, exist_ok=True)


def setup_mqtt_client():
    mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv5)
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqtt_client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                         cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS, ciphers=None)
    mqtt_client.connect(MQTT_BROKER, port=MQTT_PORT)
    mqtt_client.loop_start()
    print("Connected to MQTT Broker")
    return mqtt_client


def read_temperature_humidity():
    try:
        temperature_c = dht_device.temperature
        humidity = dht_device.humidity
        return temperature_c, humidity
    except RuntimeError:
        return None, None


def detect_number_plate(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error loading image {image_path}")
        return None

    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    plates = plateCascade.detectMultiScale(imgGray, 1.1, 4)

    for (x, y, w, h) in plates:
        plate_roi = img[y:y + h, x:x + w]
        plate_gray = cv2.cvtColor(plate_roi, cv2.COLOR_BGR2GRAY)
        _, plate_thresh = cv2.threshold(plate_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # OCR Extraction
        plate_text = pytesseract.image_to_string(plate_thresh, config='--psm 6').strip()
        plate_text = "".join([c for c in plate_text if c.isalnum()])

        if plate_text:
            save_file = os.path.join(detected_plates_folder, f"plate_{time.time()}.jpg")
            cv2.imwrite(save_file, plate_thresh)
            print(f"Detected Plate: {plate_text}")
            return plate_text

    return None


def publish_sensor_reading(mqtt_client, topic, message):
    mqtt_client.publish(topic, message)
    print(f"Published: {topic} → {message}")


def main():
    mqtt_client = setup_mqtt_client()

    try:
        while True:
            # Read Temperature & Humidity
            temperature_c, humidity = read_temperature_humidity()
            if temperature_c and humidity:
                publish_sensor_reading(mqtt_client, pub_topic_temperature, f"{temperature_c:.2f}°C")
                publish_sensor_reading(mqtt_client, pub_topic_humidity, f"{humidity:.2f}%")

            # Process Image from Folder
            image_files = [f for f in os.listdir(images_folder) if os.path.isfile(os.path.join(images_folder, f))]
            if image_files:
                random_image = os.path.join(images_folder, random.choice(image_files))
                plate_number = detect_number_plate(random_image)

                if plate_number:
                    publish_sensor_reading(mqtt_client, pub_topic_ocr, f"Plate: {plate_number}")

            time.sleep(5)

    except KeyboardInterrupt:
        print("Exiting Program")

    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Disconnected from MQTT")


if __name__ == "__main__":
    main()
How This Works
Connects Raspberry Pi to MQTT Broker.
Reads temperature and humidity from the DHT11 sensor.
Selects a random image from the folder and detects number plates.
Extracts plate number using Tesseract OCR.
Sends all data to MQTT topics:
Temperature (topic/sensors/temperature)
Humidity (topic/sensors/humidity)
Number Plate (topic/sensors/ocr)
Run This Code on Raspberry Pi
Ensure MQTT, OpenCV, and Tesseract are installed.
Modify paths for images and Haar cascade.
Run the script:
bash
Copy
Edit
python3 number_plate_mqtt.py
Now, your Raspberry Pi will detect number plates and send the data to your MQTT broker! 🚀
