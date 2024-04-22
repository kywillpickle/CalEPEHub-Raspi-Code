# Created by Kyle Pickle for use with the CLTC's CalEPEHub project

import flask_app

import threading

if __name__ == '__main__':
    # Flask front-end web interface (flask_app.py)
    flask_thread = threading.Thread(target=flask_app.run_flask)
    flask_thread.start()
