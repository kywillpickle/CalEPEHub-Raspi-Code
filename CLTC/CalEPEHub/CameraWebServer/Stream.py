# Created by Kyle Pickle for use with the CLTC's CalEPEHub project

from enum import IntEnum
import io
from multiprocessing import Lock, Process, shared_memory
import time

import cv2, sys, numpy, os
from pathlib import Path

from picamera2 import Picamera2
from libcamera import controls

CAM_WIDTH  = 640
CAM_HEIGHT = 480
CAM_PIXELS = 3
CAM_BYTES = CAM_WIDTH*CAM_HEIGHT*CAM_PIXELS

class IndConfig(IntEnum):
    """Supported occupancy indicator configurations"""
    LOW_RED    = 1
    HIGH_RED   = 2
    HIGH_GREEN = 3
    HIGH_BLUE  = 4

class SensorType(IntEnum):
    """Map of supported troffers to their respective indicator configuration"""
    DAINTREE = IndConfig.HIGH_GREEN
    ACUITY   = IndConfig.HIGH_GREEN
    SIGNIFY  = IndConfig.HIGH_RED
    ALEO     = IndConfig.LOW_RED
    COOPER   = IndConfig.HIGH_BLUE

class Statuses(IntEnum):
    """Enumerated possible occupancy detection states"""
    OFFLINE = 1
    UNOCC = 2
    OCC = 3

class Stream(object):
    """Singleton class in charge of image processing and occupancy detection"""
    _lock = Lock()                                                  # Lock to ensure only one camera instance is created
    _inst = None                                                    # Singleton Stream instance
    _process: Process = None                                        # Child process that reads frames from camera
    
    frame = shared_memory.SharedMemory(create=True, size=CAM_BYTES) # Current frame is stored here by child process
    status = shared_memory.SharedMemory(create=True, size=4)        # Current occupancy state to send to the front-end
    last_access = 0                                                 # Time of last client access to the camera
    sensor_type = SensorType.ALEO                                   # The type of sensor being processed for this stream

    def __init__(self):
        raise NotImplementedError()
    
    def __new__(cls):
        stream = object.__new__(cls)
        # start background frame thread
        Stream._process = Process(target=cls._camera_loop, args=(cls.sensor_type, cls.frame.name, cls.status.name, cls._lock))
        Stream._process.start()

        # wait until frames start to be available
        while stream.frame is None:
            time.sleep(0.01)
        
        return stream

    @classmethod
    def get_inst(cls):
        """Singleton class method that ensures atomic access to
        the single Simulator object
        """
        if(cls._inst == None):
            with cls._lock:
                if(cls._inst == None): cls._inst = cls.__new__(cls)
        return cls._inst

    def get_frame(self):
        """Gets the current image-processed camera frame,
        updated at 10 FPS
        """
        Stream.last_access = time.time()
        with self._lock:
            array = numpy.ndarray((CAM_HEIGHT, CAM_WIDTH, CAM_PIXELS), numpy.uint8, buffer=self.frame.buf)
            return cv2.imencode('.jpg', array)[1].tobytes()
    
    def get_status(self):
        """Gets the current Occupancy status as a string"""
        match int.from_bytes(self.status.buf, "big"):
            case Statuses.UNOCC:
                return 'Unoccupied'
            case Statuses.OCC:
                return 'Occupied'
            case _:
                return 'Camera Offline'

    @classmethod
    def _camera_loop(cls, sensor_type: SensorType, frame_id: str, status_id: str, lock):
        """Private image-processing thread created and manged by
        the Stream object on initialization
        """
        # Start the camera instance
        camera = Picamera2()
        camera.start()

        try:
            # Connect to shared memory
            frame = shared_memory.SharedMemory(frame_id, create=False, size=CAM_BYTES) # Current frame is stored here by child process
            status = shared_memory.SharedMemory(status_id, create=False, size=4)       # Current occupancy state to send to the front-end
            
            while True:
                # Get the raw capture from the camera and blur it
                raw_capture = cv2.cvtColor(camera.capture_array(), cv2.COLOR_BGR2RGB)
                process_buff = cv2.GaussianBlur(raw_capture, (7, 7), 0)

                # Apply color thresholding for green
                process_buff = cv2.cvtColor(process_buff, cv2.COLOR_RGB2HSV)
                lower_HSV = numpy.array([0, 0, 0])
                upper_HSV = numpy.array([0, 0, 0])
                if(sensor_type == IndConfig.LOW_RED):
                    lower_HSV = numpy.array([120, 30, 80])
                    upper_HSV = numpy.array([150, 240, 240])
                elif(sensor_type == IndConfig.HIGH_RED):
                    lower_HSV = numpy.array([120, 60, 60])
                    upper_HSV = numpy.array([150, 240, 240])
                elif(sensor_type == IndConfig.HIGH_GREEN):
                    lower_HSV = numpy.array([40, 45, 45])
                    upper_HSV = numpy.array([80, 255, 255])
                elif(sensor_type == IndConfig.HIGH_BLUE):
                    lower_HSV = numpy.array([0, 100, 100])
                    upper_HSV = numpy.array([40, 255, 150])
                color_mask = cv2.inRange(process_buff, lower_HSV, upper_HSV)
                
                # Find contours in the mask
                contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # Filter contours based on circularity and size
                filtered_contours = []
                circularity_threshold = 0.70    # Minimum circularity as a ratio of perimeter:radius
                area_threshold = 40             # Minimum area threshold in pixels
                for contour in contours:
                    # Calculate circularity
                    area = cv2.contourArea(contour)
                    perimeter = cv2.arcLength(contour, True)
                    if perimeter == 0: continue
                    circularity = 4 * numpy.pi * area / (perimeter * perimeter)

                    # Filter contours based on thresholds
                    if area > area_threshold and circularity > circularity_threshold:
                        filtered_contours.append(contour)

                # Draw detected contours on the frame
                if(sensor_type == IndConfig.LOW_RED or sensor_type == IndConfig.HIGH_RED):
                    cv2.drawContours(raw_capture, filtered_contours, -1, (0, 0, 255), 2)
                elif(sensor_type == IndConfig.HIGH_GREEN):
                    cv2.drawContours(raw_capture, filtered_contours, -1, (0, 255, 0), 2)
                elif(sensor_type == IndConfig.HIGH_BLUE):
                    cv2.drawContours(raw_capture, filtered_contours, -1, (255, 0, 0), 2)
                
                with lock:
                    # Encode frame and store in stream object
                    frame.buf[:] = raw_capture.tobytes()
                    # Update the status
                    if(len(filtered_contours) > 0): status.buf[:] = Statuses.OCC.to_bytes(4, 'big')
                    else: status.buf[:] = Statuses.UNOCC.to_bytes(4, 'big')
                time.sleep(0)
        except KeyboardInterrupt:
            pass
        finally:
            frame.close()
            frame.unlink()
            status.close()
            status.unlink()        