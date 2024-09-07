#TODO: Download a YouTube video and convert it to MJPG format using yt-dlp and ffmpeg-python @Karan


'''
pip install yt-dlp ffmpeg-python
'''

import yt_dlp
import ffmpeg

def download_youtube_video(url, output_filename='video.mp4'):
    ydl_opts = {
        'format': 'bestvideo+bestaudio',
        'merge_output_format': 'mp4',
        'outtmpl': output_filename,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print(f"Downloaded video saved as {output_filename}")

def convert_to_mjpg(input_filename, output_filename='output.mjpg', quality=2):
    print(f"Converting {input_filename} to MJPG format...")
    (
        ffmpeg
        .input(input_filename)
        .output(output_filename, vcodec='mjpeg', qscale=quality, an=None)
        .run(overwrite_output=True)
    )
    print(f"Conversion complete! MJPG video saved as {output_filename}")

if __name__ == "__main__":
    youtube_url = 'https://www.youtube.com/watch?v=example'  # Replace with your YouTube URL
    video_filename = 'video.mp4'
    mjpg_filename = 'output.mjpg'

    # Step 1: Download the YouTube video
    download_youtube_video(youtube_url, video_filename)

    # Step 2: Convert the downloaded video to MJPG format
    convert_to_mjpg(video_filename, mjpg_filename)

    print("Process completed successfully!")