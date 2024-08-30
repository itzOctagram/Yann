import cv2
import subprocess
import json
import streamlink

# Step 1: Get the video stream URL from the YouTube link using streamlink
url = 'https://www.youtube.com/watch?v=VPIyS0mbsvk'
streams = streamlink.streams(url)
stream_url = streams['best'].url

# Step 2: Use OpenCV to read the video stream
cap = cv2.VideoCapture(stream_url)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow('Live Stream', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()