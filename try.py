import cv2
import numpy as np
import requests
import time


def get_image_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        image_array = np.frombuffer(response.content, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return image
    else:
        print(f"Failed to retrieve image. Status code: {response.status_code}")
        return None


url = "http://103.217.216.197:8001/jpg/image.jpg"

cv2.namedWindow("IP Camera Stream", cv2.WINDOW_NORMAL)

while True:
    frame = get_image_from_url(url)

    if frame is not None:
        cv2.imshow("IP Camera Stream", frame)
        print("Frame displayed")
    else:
        print("Failed to grab frame")

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # Wait for a short time before requesting the next image
    # time.sleep(1)  # Adjust this value to control the refresh rate

cv2.destroyAllWindows()