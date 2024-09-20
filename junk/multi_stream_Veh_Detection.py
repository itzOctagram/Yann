import cv2
import numpy as np
import torch
import yolov5
import asyncio
import websockets
import json
import random
import streamlink

# Global variables for ROIs
roi_points_live = []
roi_polygon_live = None
roi_points_youtube = []
roi_polygon_youtube = None


def click_event_live(event, x, y, flags, param):
    global roi_points_live, roi_polygon_live
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points_live.append((x, y))
        if len(roi_points_live) == 4:
            roi_polygon_live = np.array(roi_points_live, np.int32)
            roi_polygon_live = roi_polygon_live.reshape((-1, 1, 2))


def click_event_youtube(event, x, y, flags, param):
    global roi_points_youtube, roi_polygon_youtube
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points_youtube.append((x, y))
        if len(roi_points_youtube) == 4:
            roi_polygon_youtube = np.array(roi_points_youtube, np.int32)
            roi_polygon_youtube = roi_polygon_youtube.reshape((-1, 1, 2))


async def send_detection_data(data):
    async with websockets.connect("ws://localhost:8765/sender") as websocket:
        await websocket.send(json.dumps(data))
        print(f"Sent data: {data}")

# Load YOLO model
model = yolov5.load('yolov5s.pt')

# Open live stream and YouTube live stream
live_stream_url = 'http://181.57.169.89:8080/mjpg/video.mjpg'
youtube_url = 'https://www.youtube.com/watch?v=HaF5j33VyCI'

# Use streamlink to get the best YouTube live stream URL
streams = streamlink.streams(youtube_url)
youtube_stream_url = streams['best'].url

# Open video captures
cap_live = cv2.VideoCapture(live_stream_url)
cap_youtube = cv2.VideoCapture(youtube_stream_url)

# Check if both video captures are opened successfully
if not cap_live.isOpened() or not cap_youtube.isOpened():
    print("Error: Could not open one or both video streams.")
    exit()

# Function to handle ROI selection


def select_roi(cap, window_name, click_event_fn):
    global roi_points_live, roi_polygon_live, roi_points_youtube, roi_polygon_youtube

    if window_name == 'Live Stream ROI Selection':
        roi_points = roi_points_live
        roi_polygon = roi_polygon_live
        click_event_fn = click_event_live
    elif window_name == 'YouTube Stream ROI Selection':
        roi_points = roi_points_youtube
        roi_polygon = roi_polygon_youtube
        click_event_fn = click_event_youtube

    ret, frame = cap.read()
    if not ret:
        print(f"Failed to grab first frame from {window_name}")
        exit()

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, click_event_fn)

    print(
        f"Click 4 points to define the ROI for {window_name}. Press 'q' when done.")

    while len(roi_points) < 4:
        display_frame = frame.copy()
        for point in roi_points:
            cv2.circle(display_frame, point, 5, (0, 255, 0), -1)
        cv2.imshow(window_name, display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyWindow(window_name)


# Select ROIs for both streams
select_roi(cap_live, 'Live Stream ROI Selection', click_event_live)
select_roi(cap_youtube, 'YouTube Stream ROI Selection', click_event_youtube)

# Initialize vehicle counts
counts = {
    "live": {"current": {"car": 0, "bus": 0, "motorcycle": 0}, "total": {"car": 0, "bus": 0, "motorcycle": 0}},
    "youtube": {"current": {"car": 0, "bus": 0, "motorcycle": 0}, "total": {"car": 0, "bus": 0, "motorcycle": 0}}
}

prev_counts = {
    "live": {"car": 0, "bus": 0, "motorcycle": 0},
    "youtube": {"car": 0, "bus": 0, "motorcycle": 0}
}

while True:
    ret_live, frame_live = cap_live.read()
    ret_youtube, frame_youtube = cap_youtube.read()

    if not ret_live or not ret_youtube:
        print("Failed to capture frame from one or both streams")
        break

    # Process the live stream frame
    display_frame_live = frame_live.copy()
    if roi_polygon_live is not None:
        cv2.polylines(display_frame_live, [
                      roi_polygon_live], True, (255, 0, 0), 2)

    results_live = model(frame_live)
    counts["live"]["current"]["car"] = 0
    counts["live"]["current"]["bus"] = 0
    counts["live"]["current"]["motorcycle"] = 0

    for det in results_live.pred[0]:
        class_id = int(det[5])
        x1, y1, x2, y2 = map(int, det[:4])
        center = ((x1 + x2) // 2, (y1 + y2) // 2)
        lane = 0
        if roi_polygon_live is not None and cv2.pointPolygonTest(roi_polygon_live, center, False) >= 0:

            if model.names[class_id] == 'car':
                counts["live"]["current"]["car"] += 1
                cv2.rectangle(display_frame_live, (x1, y1),
                              (x2, y2), (0, 255, 0), 2)
            elif model.names[class_id] == 'bus':
                counts["live"]["current"]["bus"] += 1
                cv2.rectangle(display_frame_live, (x1, y1),
                              (x2, y2), (255, 255, 0), 2)
            elif model.names[class_id] == 'motorcycle':
                counts["live"]["current"]["motorcycle"] += 1
                cv2.rectangle(display_frame_live, (x1, y1),
                              (x2, y2), (0, 0, 255), 2)
            if model.names[class_id] in ['car', 'bus', 'motorcycle']:
                will_turn = random.choice([True, False])
                if model.names[class_id] != 'motorcycle':
                    lane = 2 if will_turn else random.choice([1, 2])
                detection_data = {
                    "direction": 1,
                    "lane": lane,
                    "vehicleClass": model.names[class_id],
                    "willTurn": will_turn
                }
                if counts["live"]["current"][model.names[class_id]] > prev_counts["live"][model.names[class_id]]:
                    print("live")
                    asyncio.get_event_loop().run_until_complete(send_detection_data(detection_data))

    # Update total counts for live stream
    for vehicle_type in ["car", "bus", "motorcycle"]:
        # print(counts["live"]["current"][vehicle_type],
        #       prev_counts["live"][vehicle_type])
        if counts["live"]["current"][vehicle_type] > prev_counts["live"][vehicle_type]:
            counts["live"]["total"][vehicle_type] += (
                counts["live"]["current"][vehicle_type] - prev_counts["live"][vehicle_type])
            prev_counts["live"][vehicle_type] = counts["live"]["current"][vehicle_type]
    for vehicle_type in ["car", "bus", "motorcycle"]:
        prev_counts["live"][vehicle_type] = counts["live"]["current"][vehicle_type]
    # Add counts to the frame
    cv2.putText(display_frame_live, f'Total Cars: {counts["live"]["total"]["car"]}', (
        10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(display_frame_live, f'Total Buses: {counts["live"]["total"]["bus"]}', (
        10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    cv2.putText(display_frame_live, f'Total Motorcycles: {counts["live"]["total"]["motorcycle"]}', (
        10, 230), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Process the YouTube stream frame
    display_frame_youtube = frame_youtube.copy()
    if roi_polygon_youtube is not None:
        cv2.polylines(display_frame_youtube, [
                      roi_polygon_youtube], True, (255, 0, 0), 2)

    results_youtube = model(frame_youtube)
    counts["youtube"]["current"]["car"] = 0
    counts["youtube"]["current"]["bus"] = 0
    counts["youtube"]["current"]["motorcycle"] = 0

    for det in results_youtube.pred[0]:
        class_id = int(det[5])
        x1, y1, x2, y2 = map(int, det[:4])
        center = ((x1 + x2) // 2, (y1 + y2) // 2)
        lane = 0
        if roi_polygon_youtube is not None and cv2.pointPolygonTest(roi_polygon_youtube, center, False) >= 0:

            if model.names[class_id] == 'car':
                counts["youtube"]["current"]["car"] += 1
                cv2.rectangle(display_frame_youtube, (x1, y1),
                              (x2, y2), (0, 255, 0), 2)
            elif model.names[class_id] == 'bus':
                counts["youtube"]["current"]["bus"] += 1
                cv2.rectangle(display_frame_youtube, (x1, y1),
                              (x2, y2), (255, 255, 0), 2)
            elif model.names[class_id] == 'motorcycle':
                counts["youtube"]["current"]["motorcycle"] += 1
                cv2.rectangle(display_frame_youtube, (x1, y1),
                              (x2, y2), (0, 0, 255), 2)
            if model.names[class_id] in ['car', 'bus', 'motorcycle']:
                will_turn = random.choice([True, False])
                if model.names[class_id] != 'motorcycle':
                    lane = 2 if will_turn else random.choice([1, 2])
                detection_data = {
                    "direction": 1,
                    "lane": lane,
                    "vehicleClass": model.names[class_id],
                    "willTurn": will_turn
                }
                if counts["youtube"]["current"][model.names[class_id]] > prev_counts["youtube"][model.names[class_id]]:
                    print("youtube")
                    asyncio.get_event_loop().run_until_complete(send_detection_data(detection_data))

    # Update total counts for YouTube stream
    for vehicle_type in ["car", "bus", "motorcycle"]:
        # print(counts["youtube"]["current"][vehicle_type],
        #   prev_counts["youtube"][vehicle_type])
        if counts["youtube"]["current"][vehicle_type] > prev_counts["youtube"][vehicle_type]:
            counts["youtube"]["total"][vehicle_type] += (
                counts["youtube"]["current"][vehicle_type] - prev_counts["youtube"][vehicle_type])
            prev_counts["youtube"][vehicle_type] = counts["youtube"]["current"][vehicle_type]
    for vehicle_type in ["car", "bus", "motorcycle"]:
        prev_counts["youtube"][vehicle_type] = counts["youtube"]["current"][vehicle_type]

    # Add counts to the frame
    cv2.putText(display_frame_youtube, f'Total Cars: {counts["youtube"]["total"]["car"]}', (
        10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(display_frame_youtube, f'Total Buses: {counts["youtube"]["total"]["bus"]}', (
        10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    cv2.putText(display_frame_youtube, f'Total Motorcycles: {counts["youtube"]["total"]["motorcycle"]}', (
        10, 230), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Display the processed frames
    cv2.imshow('Live Stream', display_frame_live)
    cv2.imshow('YouTube Stream', display_frame_youtube)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap_live.release()
cap_youtube.release()
cv2.destroyAllWindows()
