Since your Raspberry Pi is using **MQTT (with Mosquitto or HiveMQ)** as the messaging system, you can push the generated data from your Python program to the Raspberry Pi using **MQTT protocol**. Below is a step-by-step guide to achieving this.  

---

## **1. Setup MQTT Broker on Raspberry Pi**  
If you haven't already, install and set up **Mosquitto** as the MQTT broker on the Raspberry Pi.  

### **Install Mosquitto**
```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
```

### **Enable and Start Mosquitto Service**
```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### **Verify Mosquitto is Running**
```bash
mosquitto_sub -h localhost -t "test/topic"
```
(Open another terminal and publish a message)
```bash
mosquitto_pub -h localhost -t "test/topic" -m "Hello from MQTT!"
```

If you see "Hello from MQTT!" on the subscriber terminal, the broker is working.

---

## **2. Install Paho MQTT Library on Your Laptop**
On your **laptop**, install the `paho-mqtt` library:
```bash
pip install paho-mqtt
```

---

## **3. Publish Data from Python Program on Laptop**
Modify your Python program to **send data** to the Raspberry Pi over MQTT.

### **Python Script to Publish Data**
```python
import paho.mqtt.client as mqtt
import json
import time

# MQTT Broker (Change to your Raspberry Pi's IP)
MQTT_BROKER = "raspberrypi.local"  # Or use the IP e.g., "192.168.1.100"
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/data"

# Initialize MQTT client
client = mqtt.Client()

# Connect to MQTT broker
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Generate and send data
for i in range(10):
    data = {
        "id": i,
        "value": round(100 * i, 2),
        "timestamp": time.time()
    }
    client.publish(MQTT_TOPIC, json.dumps(data))
    print(f"Published: {data}")
    time.sleep(2)  # Simulate data generation delay

client.disconnect()
```
🔹 This script **publishes JSON data** to the topic `sensor/data` on the Raspberry Pi MQTT broker.

---

## **4. Subscribe to MQTT Data on Raspberry Pi**
On your **Raspberry Pi**, create a Python script to subscribe to the incoming data.

### **Python Script to Subscribe on Raspberry Pi**
```python
import paho.mqtt.client as mqtt
import json

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/data"

# Callback function when message is received
def on_message(client, userdata, message):
    data = json.loads(message.payload.decode("utf-8"))
    print(f"Received Data: {data}")

# Initialize MQTT Client
client = mqtt.Client()
client.on_message = on_message

# Connect to broker and subscribe
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC)

print("Listening for incoming data...")
client.loop_forever()
```

✅ **Now, when your laptop sends data, the Raspberry Pi will receive and print it.**  

---

## **5. Secure the MQTT Connection (Optional)**
For security, you can:  
- Add **username/password authentication** to Mosquitto.  
- Use **TLS encryption** for secure communication.  

Example:  
Modify `/etc/mosquitto/mosquitto.conf` on Raspberry Pi to enable authentication:
```
allow_anonymous false
password_file /etc/mosquitto/passwd
```
Create a username/password:
```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd myuser
sudo systemctl restart mosquitto
```
Modify the Python script on the laptop to include authentication:
```python
client.username_pw_set("myuser", "mypassword")
```

---

## **Final Summary**
| **Step** | **Action** |
|----------|------------|
| **1** | Install Mosquitto on Raspberry Pi (`sudo apt install mosquitto`) |
| **2** | Install `paho-mqtt` on your laptop (`pip install paho-mqtt`) |
| **3** | Write a Python script on the **laptop** to publish data to MQTT |
| **4** | Write a Python script on the **Raspberry Pi** to subscribe to data |
| **5** | (Optional) Secure MQTT using authentication & TLS |

Now, your laptop can generate data and **push it to the Raspberry Pi via MQTT**!

🚀 **Let me know if you need modifications!** 🚀
