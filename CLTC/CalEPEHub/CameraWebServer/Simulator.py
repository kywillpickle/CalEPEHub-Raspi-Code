from enum import Enum
import json
import math
import threading
import time

from MqttBroker import MqttBroker

CELL_SIZE = 3.0 # ft

class Pattern(Enum):
    """Supported occupancy indicator configurations"""
    UP_AND_DOWN = 1 # Robot is moving down, up, over...
    ALTERNATE   = 2 # Robot is moving down, over, up, over...

class Status(Enum):
    """Possible statuses of the simulation thread"""
    STOPPED          = 1 # Simulator is not running
    STOPPING         = 2 # Simulator has be flagged to stop
    RUNNING_SENDING  = 3 # Simulator is running; awaiting status from robot
    RUNNING_RECEIVED = 4 # Simulator is running; waiting `step` before proceeding

class Simulator(object):
    """Singleton class in charge of simulating the test (move forward, turn left, etc.)"""
    _lock = threading.RLock()     # Lock to ensure atomicity of Simulator instance and status
    _inst = None                  # Singleton Simulator instance
    _thread = None                # Background thread that runs the test
    status = Status.STOPPED       # Current status of the Simulator thread

    x_pos = 0                     # The current X position of the robot (# cells)
    y_pos = 1                     # The current Y position of the robot (# cells)
    angle = 270                   # The current angle of the robot (deg)
    width = 0                     # The set width of the grid (# cells)
    height = 0                    # The set height of the grid (# cells)
    step = 0                      # The set step time in between cells (seconds)
    n_trials = 1                  # The # of times to conduct the test
    pattern = Pattern.UP_AND_DOWN # The configured pattern for the robot to follow

    def __init__(self):
        raise NotImplementedError()
    
    def __new__(cls):
        simulator = object.__new__(cls)
        # init background simulation thread
        cls._thread = threading.Thread(target=simulator._sim_loop)

        return simulator
    
    @classmethod
    def get_inst(cls):
        """Singleton class method that ensures atomic access to
        the single Simulator object
        """
        with cls._lock:
            if(cls._inst == None): cls._inst = cls.__new__(cls)
        return cls._inst
    
    def start_test(self, grid_size, step_time, num_trials, pattern):
        self.stop_test()
        # Wait for thread to close
        while self.status != Status.STOPPED: time.sleep(0)
        self.x_pos = 0
        self.y_pos = grid_size[1]
        self.width = grid_size[0]
        self.height = grid_size[1]
        self.step = step_time
        self.n_trials = num_trials
        if(pattern == 'up-and-down'): pattern = Pattern.UP_AND_DOWN
        else: pattern = Pattern.ALTERNATE
        self.status = Status.RUNNING_RECEIVED
        self._thread.start()
        return
    
    def stop_test(self):
        with self._lock:
            if self.status != Status.STOPPED:
                self.status = Status.STOPPING
        return
    
    def _move_to(self, x, y):
        # Calculate and send command
        with self._lock: # Ensure atomicity
            if self.status == Status.STOPPING: return
            self.path(x, y)
        # Wait for update
        # while self.status == Status.RUNNING_SENDING: time.sleep(0)
        # Wait for one complete step
        end_step = time.time() + self.step
        while time.time() < end_step: time.sleep(0)
    
    def _sim_loop(self):
        if self.pattern == Pattern.UP_AND_DOWN:
            for x in range(0, self.width):
                         #    Go forwards...           Then backwards
                for y in list(range(self.height-1, -1, -1)) + list(range(1, self.height)):
                    self._move_to(x, y)
        elif self.pattern == Pattern.ALTERNATE:
            for x in range(0, self.width):
                if(x % 2 == 0):
                    # If even, move down
                    for y in range(self.height-1, -1, -1):
                        self._move_to(x, y)
                else:
                    # If odd, move back up
                    for y in range(0, self.height):
                        self._move_to(x, y)
        self.status = Status.STOPPED
        return
    
    def path(self, x, y):
        delta_x = x - self.x_pos
        delta_y = y - self.y_pos

        dist = math.sqrt(delta_x*delta_x + delta_y*delta_y)*CELL_SIZE
        angle = math.degrees(math.atan2(delta_y, delta_x)) - self.angle
        angle = (angle + 180) % 360 - 180
        print(delta_x, delta_y, dist, angle)
        MqttBroker.get_inst().send_command({"cmd":"path", "args":{"delta": dist, "theta": angle}})
        self.x_pos = x
        self.y_pos = y
        self.angle = (self.angle + angle + 180) % 360 - 180
        self.status = Status.RUNNING_SENDING

