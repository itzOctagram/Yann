import cv2
import numpy as np
import yolov5
from typing import Literal
import streamlink
import asyncio
import websockets
import json
import random
import warnings
import requests
import threading
import asyncio
warnings.filterwarnings("ignore", category=FutureWarning)


async def send_detection_data(data):
    async with websockets.connect("ws://localhost:8765/sender") as websocket:
        await websocket.send(json.dumps(data))
        print(f"Sent data: {data}")


class VehicleCounts:
    car: int
    bus: int
    motorcycle: int

    def __init__(self, car: int = 0, bus: int = 0, motorcycle: int = 0):
        self.car = car
        self.bus = bus
        self.motorcycle = motorcycle


class Stream:
    url: str
    type: Literal["youtube", "image", "mjpg"]
    label: str
    cap: cv2.VideoCapture
    roi_points: list
    roi_polygon = None
    total_counts: VehicleCounts
    current_counts: VehicleCounts
    prev_counts: VehicleCounts

    def __init__(self, url: str, type: Literal["youtube", "image", "mjpg"], label: str = "Camera"):
        self.url = url
        self.type = type
        self.label = label
        self.cap = None
        self.roi_points = []
        self.roi_polygon = None
        self.total_counts = VehicleCounts()
        self.current_counts = VehicleCounts()
        self.prev_counts = VehicleCounts()

    def getFrame(self):
        print(f"Getting frame {self.label}")
        if (self.cap != None) and (self.type != "image"):
            return self.cap.read()

        if (self.type == "youtube"):
            streams = streamlink.streams(self.url)
            stream_url = streams['best'].url
            cap = cv2.VideoCapture(stream_url)

        elif (self.type == "image"):
            response = requests.get(self.url)
            if response.status_code == 200:
                image_array = np.frombuffer(response.content, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                return (response.status_code == 200, image)
            else:
                return (response.status_code == 200, None)

        elif (self.type == "mjpg"):
            cap = cv2.VideoCapture(self.url)

        self.cap = cap
        return cap.read()

    def selectROI(self):
        ret, frame = self.getFrame()
        if not ret:
            print("Failed to grab first frame")
            exit()

        cv2.namedWindow(f'ROI Selection - {self.label}')
        cv2.setMouseCallback(f'ROI Selection - {self.label}', self.click_event)

        # Instructions
        print("Click 4 points to define the ROI. Press 'q' when done.")

        while len(self.roi_points) < 4:
            display_frame = frame.copy()
            for point in self.roi_points:
                cv2.circle(display_frame, point, 5, (0, 255, 0), -1)
            cv2.imshow(f'ROI Selection - {self.label}', display_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyWindow(f'ROI Selection - {self.label}')

    def click_event(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.roi_points.append((x, y))
            if len(self.roi_points) == 4:
                self.roi_polygon = np.array(self.roi_points, np.int32)
                self.roi_polygon = self.roi_polygon.reshape((-1, 1, 2))


class StreamThread(threading.Thread):
    def __init__(self, stream: Stream, model):
        threading.Thread.__init__(self)
        self.stream = stream
        self.model = model

    def run(self):
        print(f'\033[92mThread for {self.stream.label} started\033[0m')
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            ret, frame = self.stream.getFrame()
            if not ret:
                print("Failed to grab frame")
                break

            # Create a copy of the frame to draw on
            display_frame = frame.copy()

            # Draw ROI polygon
            if self.stream.roi_polygon is not None:
                cv2.polylines(display_frame, [
                    self.stream.roi_polygon], True, (255, 0, 0), 2)

            # Perform detection
            results = model(frame)

            # Reset current counts for this frame
            self.stream.current_counts = VehicleCounts()

            for det in results.pred[0]:
                class_id = int(det[5])
                x1, y1, x2, y2 = map(int, det[:4])
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
                lane = 0
                # Check if the center of the object is in the ROI
                if self.stream.roi_polygon is not None and cv2.pointPolygonTest(self.stream.roi_polygon, center, False) >= 0:
                    if model.names[class_id] == 'car':
                        self.stream.current_counts.car += 1
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2),
                                      (0, 255, 0), 2)  # Green for cars
                        # lane = random.choice([1, 2])  # Randomly set lane
                    elif model.names[class_id] == 'bus':
                        self.stream.current_counts.bus += 1
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2),
                                      (255, 255, 0), 2)  # Blue for buses
                        # lane = random.choice([1, 2])  # Randomly set lane
                    elif model.names[class_id] == 'motorcycle':
                        self.stream.current_counts.motorcycle += 1
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2),
                                      (0, 0, 255), 2)  # Red for motorcycles
                        lane = 0  # Motorcycles use lane 1
                    if (model.names[class_id] == 'car' or model.names[class_id] == 'bus' or model.names[class_id] == 'motorcycle'):
                        # Randomly set willTurn
                        will_turn = random.choice([True, False])
                        if (model.names[class_id] != 'motorcycle'):
                            if (will_turn):
                                lane = 2
                            else:
                                lane = random.choice([1, 2])
                        # Create detection data
                        detection_data = {
                            "direction": 1,  # This could be updated based on your needs
                            "lane": lane,
                            "vehicleClass": model.names[class_id],
                            "willTurn": will_turn,
                            "label" : self.stream.label
                        }
                        if ((model.names[class_id] == 'car' and self.stream.current_counts.car > self.stream.prev_counts.car) or (model.names[class_id] == 'bus' and self.stream.current_counts.bus > self.stream.prev_counts.bus) or (model.names[class_id] == 'motorcycle' and self.stream.current_counts.motorcycle > self.stream.prev_counts.motorcycle)):
                            # Send data to WebSocket server
                            loop.run_until_complete(
                                send_detection_data(detection_data))

            # Update total counts only if the current counts have changed
            if self.stream.current_counts.car > self.stream.prev_counts.car:
                self.stream.total_counts.car += (self.stream.current_counts.car -
                                            self.stream.prev_counts.car)
            if self.stream.current_counts.bus > self.stream.prev_counts.bus:
                self.stream.total_counts.bus += (self.stream.current_counts.bus -
                                            self.stream.prev_counts.bus)
            if self.stream.current_counts.motorcycle > self.stream.prev_counts.motorcycle:
                self.stream.total_counts.motorcycle += (self.stream.current_counts.motorcycle -
                                                   self.stream.prev_counts.motorcycle)

            # Update previous counts
            self.stream.prev_counts.car = self.stream.current_counts.car
            self.stream.prev_counts.bus = self.stream.current_counts.bus
            self.stream.prev_counts.motorcycle = self.stream.current_counts.motorcycle

            # Predefine text positions and properties
            text_positions = [
                (f'Total Cars: {self.stream.total_counts.car}',
                 (10, 70), (0, 255, 0)),
                (f'Total Buses: {self.stream.total_counts.bus}',
                 (10, 150), (255, 255, 0)),
                (f'Total Motorcycles: {self.stream.total_counts.motorcycle}',
                 (10, 230), (0, 0, 255))
            ]

            # Add counts to the frame
            for text, position, color in text_positions:
                cv2.putText(display_frame, text, position,
                            cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

            # Display result
            cv2.imshow(f'Vehicle Detection - {self.stream.label}', display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print(f'\033[91mThread for {self.stream.label} stopped\033[0m')  # Red text
                break


# Define streams
stream1 = Stream(
    "https://www.youtube.com/watch?v=oz46g45u80k", "youtube", "YouTube")
stream2 = Stream(
    "http://118.22.23.185:80/SnapshotJPEG?Resolution=640x480&Quality=Clarity", "image", "Image")
stream3 = Stream("http://181.57.169.89:8080/mjpg/video.mjpg", "mjpg", "MJPG")

streams = [stream3, stream1]

# Load YOLO model
model = yolov5.load('./yolov5s.pt')

# Create and start threads for each stream
threads = []
for stream in streams:
    stream.selectROI()
    thread = StreamThread(stream, model)
    threads.append(thread)

# Start all threads
for thread in threads:
    print(f'\033[94mStarting thread for {thread.stream.label}\033[0m')
    thread.start()

# Wait for all threads to finish
for thread in threads:
    print(
        f'\033[93mWaiting for thread {thread.stream.label} to finish\033[0m')
    thread.join()

# Release resources
for stream in streams:
    if stream.cap is not None:
        stream.cap.release()
cv2.destroyAllWindows()
