#TODO : @Karan try this too and let me know if it works

'''
Using threading to download and convert a YouTube stream to MJPG format and then stream it to OpenCV
'''

import cv2
import subprocess
import threading
import os

def download_and_convert_stream(youtube_url, output_filename='output.mjpg'):
    # Run FFmpeg command to convert YouTube stream to MJPG
    ffmpeg_command = [
        'ffmpeg', '-i', youtube_url, '-vcodec', 'mjpeg', '-q:v', '2',
        '-f', 'mpjpeg', output_filename
    ]
    subprocess.run(ffmpeg_command)

def stream_to_opencv(mjpg_stream_url):
    cap = cv2.VideoCapture(mjpg_stream_url)

    if not cap.isOpened():
        print("Error: Could not open MJPG stream.")
        return

    while cap.isOpened():
        ret, frame = cap.read()
        if ret:
            cv2.imshow('MJPG Stream', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    youtube_url = 'https://www.youtube.com/watch?v=example'  # Replace with your YouTube stream URL
    mjpg_filename = 'output.mjpg'  # Local file to save the MJPG stream
    
    # Convert YouTube stream to MJPG format in a separate thread
    convert_thread = threading.Thread(target=download_and_convert_stream, args=(youtube_url, mjpg_filename))
    convert_thread.start()

    # Wait for the stream to start
    while not os.path.exists(mjpg_filename):
        pass
    
    # Stream MJPG file to OpenCV
    stream_to_opencv(mjpg_filename)

    # Wait for the convert thread to finish
    convert_thread.join()

    # Clean up by removing the MJPG file
    os.remove(mjpg_filename)
