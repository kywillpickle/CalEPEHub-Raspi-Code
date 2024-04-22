# Created by Kyle Pickle for use with the CLTC's CalEPEHub project

from CLTC.CalEPEHub.CameraWebServer import flask_app
from CLTC.CalEPEHub.CameraWebServer.Simulator import Simulator
from CLTC.CalEPEHub.CameraWebServer.Stream import Stream
from CLTC.CalEPEHub.CameraWebServer.MqttBroker import MqttBroker

import threading

if __name__ == '__main__':
    # Flask front-end web interface (flask_app.py)
    flask_thread = threading.Thread(target=flask_app.run_flask)
    flask_thread.start()