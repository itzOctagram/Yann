import cv2
import numpy as np
import torch
import yolov5
import asyncio
import websockets
import json
import random

# Global variables
roi_points = [[] for _ in range(4)]
roi_polygon = [None] * 4

# Function to handle mouse clicks for ROI selection
def click_event(event, x, y, flags, param):
    stream_id = param  # Identify which stream's ROI we're selecting
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points[stream_id].append((x, y))
        if len(roi_points[stream_id]) == 4:
            roi_polygon[stream_id] = np.array(roi_points[stream_id], np.int32)
            roi_polygon[stream_id] = roi_polygon[stream_id].reshape((-1, 1, 2))

# Asynchronous function to send detection data to WebSocket server
async def send_detection_data(data):
    async with websockets.connect("ws://localhost:8765/sender") as websocket:
        await websocket.send(json.dumps(data))
        print(f"Sent data: {data}")

# Load YOLO model
model = yolov5.load('yolov5s.pt')

# List of video stream URLs
stream_urls = [
# List of video streams
    'http://181.57.169.89:8080/mjpg/video.mjpg',
    'http://181.57.169.89:8080/mjpg/video.mjpg',
    'http://181.57.169.89:8080/mjpg/video.mjpg',
    'http://181.57.169.89:8080/mjpg/video.mjpg',
]

# Initialize video captures for all streams
caps = [cv2.VideoCapture(url) for url in stream_urls]

# Set up windows for ROI selection and assign callback functions
for i in range(4):
    ret, frame = caps[i].read()
    if not ret:
        print(f"Failed to grab first frame from stream {i+1}")
        exit()
    cv2.namedWindow(f'ROI Selection {i+1}')
    cv2.setMouseCallback(f'ROI Selection {i+1}', click_event, i)

    # Instructions for ROI selection
    print(f"Click 4 points to define the ROI for stream {i+1}. Press 'q' when done.")

    while len(roi_points[i]) < 4:
        display_frame = frame.copy()
        for point in roi_points[i]:
            cv2.circle(display_frame, point, 5, (0, 255, 0), -1)
        cv2.imshow(f'ROI Selection {i+1}', display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyWindow(f'ROI Selection {i+1}')

# Initialize vehicle counts for each stream
vehicle_counts = [
    {
        "car": {"current": 0, "total": 0},
        "bus": {"current": 0, "total": 0},
        "motorcycle": {"current": 0, "total": 0}
    } for _ in range(4)
]

# Track previous counts for each stream
prev_vehicle_counts = [
    {"car": 0, "bus": 0, "motorcycle": 0} for _ in range(4)
]

async def process_frame():
    global prev_vehicle_counts

    while True:
        for i in range(4):
            ret, frame = caps[i].read()
            if not ret:
                break

            # Create a copy of the frame to draw on
            display_frame = frame.copy()

            # Draw ROI polygon
            if roi_polygon[i] is not None:
                cv2.polylines(display_frame, [roi_polygon[i]], True, (255, 0, 0), 2)

            # Perform detection
            results = model(frame)

            # Reset current counts for this frame
            for vehicle_type in vehicle_counts[i]:
                vehicle_counts[i][vehicle_type]["current"] = 0

            for det in results.pred[0]:
                class_id = int(det[5])
                x1, y1, x2, y2 = map(int, det[:4])
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
                vehicle_type = model.names[class_id]

                # Check if the center of the object is in the ROI
                if roi_polygon[i] is not None and cv2.pointPolygonTest(roi_polygon[i], center, False) >= 0:
                    if vehicle_type in vehicle_counts[i]:
                        vehicle_counts[i][vehicle_type]["current"] += 1
                        color = (0, 255, 0) if vehicle_type == "car" else (255, 255, 0) if vehicle_type == "bus" else (0, 0, 255)
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)

                        # Lane and turn prediction logic
                        will_turn = random.choice([True, False])
                        lane = 2 if will_turn else random.choice([1, 2]) if vehicle_type != "motorcycle" else 0

                        # Create detection data
                        detection_data = {
                            "direction": 1,  # This can be updated based on your needs
                            "lane": lane,
                            "vehicleClass": vehicle_type,
                            "willTurn": will_turn
                        }

                        # Send data to WebSocket server
                        await send_detection_data(detection_data)

            # Update total counts only if the current counts have changed
            for vehicle_type in vehicle_counts[i]:
                if vehicle_counts[i][vehicle_type]["current"] > prev_vehicle_counts[i][vehicle_type]:
                    vehicle_counts[i][vehicle_type]["total"] += (vehicle_counts[i][vehicle_type]["current"] - prev_vehicle_counts[i][vehicle_type])
                prev_vehicle_counts[i][vehicle_type] = vehicle_counts[i][vehicle_type]["current"]

            # Add counts to the frame
            y_pos = 70
            for vehicle_type, counts in vehicle_counts[i].items():
                color = (0, 255, 0) if vehicle_type == "car" else (255, 255, 0) if vehicle_type == "bus" else (0, 0, 255)
                cv2.putText(display_frame, f'Total {vehicle_type.capitalize()}s: {counts["total"]}', (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                y_pos += 80

            # Display result for this stream
            cv2.imshow(f'Vehicle Detection {i+1}', display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    for cap in caps:
        cap.release()
    cv2.destroyAllWindows()

# Start the frame processing loop
asyncio.run(process_frame())
