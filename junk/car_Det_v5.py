import cv2
import numpy as np
import torch
import yolov5
import asyncio
import websockets
import json
import random
import threading

# Global variables
roi_points = []
roi_polygon = None

# Load YOLO model
model = yolov5.load('yolov5s.pt')


def click_event(event, x, y, flags, param):
    global roi_points, roi_polygon
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points.append((x, y))
        if len(roi_points) == 4:
            roi_polygon = np.array(roi_points, np.int32)
            roi_polygon = roi_polygon.reshape((-1, 1, 2))


async def send_detection_data(data):
    async with websockets.connect("ws://0.tcp.in.ngrok.io:10859/sender") as websocket:
        await websocket.send(json.dumps(data))
        print(f"Sent data: {data}")


def process_video_stream(stream_url):
    global roi_points, roi_polygon
    cap = cv2.VideoCapture(stream_url)

    # Read first frame to set up ROI selection
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab first frame")
        return

    cv2.namedWindow('ROI Selection')
    cv2.setMouseCallback('ROI Selection', click_event)

    # Instructions
    print("Click 4 points to define the ROI. Press 'q' when done.")

    while len(roi_points) < 4:
        display_frame = frame.copy()
        for point in roi_points:
            cv2.circle(display_frame, point, 5, (0, 255, 0), -1)
        cv2.imshow('ROI Selection', display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyWindow('ROI Selection')

    # Initialize counts
    current_car_count = 0
    total_car_count = 0
    current_bus_count = 0
    total_bus_count = 0
    current_motorcycle_count = 0
    total_motorcycle_count = 0

    prev_car_count = 0
    prev_bus_count = 0
    prev_motorcycle_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Create a copy of the frame to draw on
        display_frame = frame.copy()

        # Draw ROI polygon
        if roi_polygon is not None:
            cv2.polylines(display_frame, [roi_polygon], True, (255, 0, 0), 2)

        # Perform detection
        results = model(frame)

        # Reset current counts for this frame
        current_car_count = 0
        current_bus_count = 0
        current_motorcycle_count = 0

        for det in results.pred[0]:
            class_id = int(det[5])
            x1, y1, x2, y2 = map(int, det[:4])
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            lane = 0
            # Check if the center of the object is in the ROI
            if roi_polygon is not None and cv2.pointPolygonTest(roi_polygon, center, False) >= 0:
                if model.names[class_id] == 'car':
                    current_car_count += 1
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2),
                                  (0, 255, 0), 2)  # Green for cars
                elif model.names[class_id] == 'bus':
                    current_bus_count += 1
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2),
                                  (255, 255, 0), 2)  # Blue for buses
                elif model.names[class_id] == 'motorcycle':
                    current_motorcycle_count += 1
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
                        "willTurn": will_turn
                    }

                    if ((model.names[class_id] == 'car' and current_car_count > prev_car_count) or (model.names[class_id] == 'bus' and current_bus_count > prev_bus_count) or (model.names[class_id] == 'motorcycle' and current_motorcycle_count > prev_motorcycle_count)):
                        # Send data to WebSocket server
                        asyncio.get_event_loop().run_until_complete(send_detection_data(detection_data))

        # Update total counts only if the current counts have changed
        if current_car_count > prev_car_count:
            total_car_count += (current_car_count - prev_car_count)
        if current_bus_count > prev_bus_count:
            total_bus_count += (current_bus_count - prev_bus_count)
        if current_motorcycle_count > prev_motorcycle_count:
            total_motorcycle_count += (current_motorcycle_count -
                                       prev_motorcycle_count)

        # Update previous counts
        prev_car_count = current_car_count
        prev_bus_count = current_bus_count
        prev_motorcycle_count = current_motorcycle_count

        # Add counts to the frame
        cv2.putText(display_frame, f'Total Cars: {total_car_count}', (
            10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(display_frame, f'Total Buses: {total_bus_count}', (
            10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        cv2.putText(display_frame, f'Total Motorcycles: {total_motorcycle_count}', (
            10, 230), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Display result
        cv2.imshow(f'Vehicle Detection - {stream_url}', display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # URLs of video streams
    video_stream_urls = [
        'http://181.57.169.89:8080/mjpg/video.mjpg',
        'http://181.57.169.89:8080/mjpg/video.mjpg'
    ]

    # Create and start a thread for each video stream
    threads = []
    for url in video_stream_urls:
        thread = threading.Thread(target=process_video_stream, args=(url,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()
