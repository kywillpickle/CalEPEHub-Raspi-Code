# Created by Kyle Pickle for use with the CLTC's CalEPEHub project

import time
from flask import Flask, jsonify, render_template, Response, request
from Simulator import Simulator
from Stream import Stream

app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')

def gen_frame(inst: Stream):
    while True:
        time.sleep(0)
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + inst.get_frame() + b'\r\n')

@app.route('/camera_feed')
def camera_feed():
    return Response(gen_frame(Stream.get_inst()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera_status')
def camera_status():
    return jsonify({'status': Stream.get_inst().get_status()})

@app.route('/start_test', methods=['POST'])
def start_test():
    data = request.get_json()
    grid_size = data.get('grid_size')
    step_time = data.get('step_time')
    num_trials = data.get('num_trials')
    pattern = data.get('pattern')
    
    if grid_size is not None and step_time is not None and num_trials is not None and pattern is not None:
        Simulator.get_inst().start_test(grid_size, step_time, num_trials, pattern)
        return jsonify({'message': 'Test parameters sent successfully'}), 200
    else:
        return jsonify({'error': 'Invalid data provided'}), 400
    
def run_flask():
    app.run(host='0.0.0.0', debug=False, threaded=True)