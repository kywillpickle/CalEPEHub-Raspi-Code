import json
import threading
import paho.mqtt.client as mqtt

class MqttBroker(object):
    _lock = threading.RLock() # Lock to ensure only one MQTT instance is created
    _inst = None              # Singleton MQTT instance

    broker_address = 'localhost' # The address of the (local) MQTT broker
    broker_port = 1883           # The port of said MQTT broker
    client: mqtt.Client = None   # The client used to connect to the MQTT broker
    _callbacks = {}              # Dict of topics and their associated callbacks

    def __init__(self):
        raise NotImplementedError()
    
    def __new__(cls):
        mqtt_broker = object.__new__(cls)
        mqtt_broker.client = mqtt.Client("camera_control")
        mqtt_broker.client.connect(mqtt_broker.broker_address, mqtt_broker.broker_port)
        mqtt_broker.client.on_message = lambda client, userdata, msg: mqtt_broker.on_message(client, userdata, msg)

        return mqtt_broker

    @classmethod
    def get_inst(cls):
        """Singleton class method that ensures atomic access to
        the single MqttBroker object
        """
        with cls._lock:
            if(cls._inst == None): cls._inst = cls.__new__(cls)
        return cls._inst
    
    def subscribe_to_topic(self, topic: str, funct):
        self.client.subscribe(topic)
        self._callbacks[topic] = funct

    def run(self):
        self.client.loop_forever()

    def send_command(self, cmd: dict):
        self.client.publish("test/cmd", json.dumps(cmd))

    def on_message(self, client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
        print(f"Received message: {message.payload.decode()}")
        # Start the test procedure when receiving the signal from the broker
        for key in self._callbacks:
            if message.topic == key:
                self._callbacks[key](message.payload.decode())


