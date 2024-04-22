import json
import threading
import paho.mqtt.client as mqtt

class MqttBroker(object):
    _lock = threading.RLock() # Lock to ensure only one MQTT instance is created
    _inst = None              # Singleton MQTT instance

    broker_address = 'localhost' # The address of the (local) MQTT broker
    broker_port = 1883           # The port of said MQTT broker
    status_messages = []         # List of all previous status messages
    client = None                # The client used to connect to the MQTT broker

    def __init__(self):
        raise NotImplementedError()
    
    def __new__(cls):
        mqtt_broker = object.__new__(cls)
        mqtt_broker.client = mqtt.Client("camera_control")
        mqtt_broker.client.connect(mqtt_broker.broker_address, mqtt_broker.broker_port)
        mqtt_broker.client.subscribe("test/status")
        mqtt_broker.client.on_message = mqtt_broker.on_message

        return mqtt_broker

    @classmethod
    def get_inst(cls):
        """Singleton class method that ensures atomic access to
        the single MqttBroker object
        """
        with cls._lock:
            if(cls._inst == None): cls._inst = cls.__new__(cls)
        return cls._inst
    
    def run(self):
        self.client.loop_forever()

    # def start_test(self, grid_size, step_time, num_trials, pattern):
    #     params = {
    #         "grid_size": grid_size,
    #         "step_time": step_time,
    #         "num_trials": num_trials,
    #         "pattern": pattern
    #     }
    #     self.client.publish("test/start", json.dumps(params))

    def send_command(self, cmd: dict):
        self.client.publish("test/cmd", json.dumps(cmd))

    def on_message(self, client, userdata, message):
        msg_str = message.payload.decode()
        try:
            msg_json = json.loads(msg_str)
            self.status_messages.append(msg_json)
        except json.JSONDecodeError:
            print("Invalid JSON message received.")

    def get_latest_status(self):
        if self.status_messages:
            return self.status_messages[-1]
        else:
            return None

