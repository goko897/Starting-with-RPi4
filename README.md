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

