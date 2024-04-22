import time
import random
import json
import paho.mqtt.client as mqtt

# MQTT broker address (IP of the Pi hosting the broker)
broker_address = "camera-calepehub.local"
broker_port = 1883

# Parameters for the test
grid_width = 19
grid_height = 19
step_time = 5
pattern = "up-and-down"

def on_message(client, userdata, message):
    print(f"Received message: {message.payload.decode()}")
    # Start the test procedure when receiving the signal from the broker
    if message.topic == "test/cmd":
        process_test_start(message.payload.decode())

def process_test_start(msg_str):
        try:
            msg_json = json.loads(msg_str)
            cmd = msg_json["cmd"]
            args = msg_json["args"]

            print(f"Received command: {cmd} with args: {args}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON message: {e}")
        except KeyError as e:
            print(f"Missing key in JSON message: {e}")

# Create MQTT client
client = mqtt.Client("robot")
client.connect(broker_address, broker_port)
client.subscribe("test/cmd")
client.on_message = on_message

# Main loop to listen for messages
client.loop_forever()
