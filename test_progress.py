#!/usr/bin/env python3

from yt_dlp import YoutubeDL

def progress_hook(d):
    print("Progress data:", d)

ydl_opts = {
    'format': 'best',
    'progress_hooks': [progress_hook],
    'quiet': True,
    'skip_download': False,  # Actually download to see progress
}

# Replace with a short video URL
video_url = 'https://www.youtube.com/watch?v=Rd7yyutb-DI'

with YoutubeDL(ydl_opts) as ydl:
    ydl.download([video_url])
