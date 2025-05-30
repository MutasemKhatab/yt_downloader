# Termux Backend (Python) - Flask + Flask-SocketIO + yt-dlp
# Save this as app.py in Termux

from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from yt_dlp import YoutubeDL
import eventlet
import subprocess
import os
import sys

# Check if FFmpeg is installed
def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Print FFmpeg status on startup
if not check_ffmpeg():
    print("WARNING: FFmpeg is not installed or not in PATH. Video and audio streams cannot be merged!")
    print("Please install FFmpeg: https://ffmpeg.org/download.html")
else:
    print("FFmpeg is installed and available for merging streams.")

@app.route('/info', methods=['POST'])
def get_video_info():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = []
    
    # First add all combined formats (with both audio and video) - exclude WebM
    for f in info.get('formats', []):
        # Skip WebM formats
        if f.get('ext') == 'webm':
            continue
            
        if (f.get('acodec') != 'none' and f.get('acodec') is not None and 
            f.get('vcodec') != 'none' and f.get('vcodec') is not None):
            
            resolution = f.get('resolution') or f"{f.get('width')}x{f.get('height')}"
            format_entry = {
                'format_id': f['format_id'],
                'ext': f['ext'],
                'resolution': resolution,
                'filesize': f.get('filesize'),
                'format_note': f.get('format_note', 'Combined'),
                'vcodec': f.get('vcodec'),
                'acodec': f.get('acodec'),
                'has_video': True,
                'has_audio': True,
            }
            formats.append(format_entry)
    
    # Then add best video+best audio combinations for higher quality options
    best_audio = None
    video_formats = []
    
    for f in info.get('formats', []):
        # Skip WebM formats
        if f.get('ext') == 'webm':
            continue
            
        # Find best audio
        if f.get('acodec') != 'none' and f.get('acodec') is not None and (best_audio is None or f.get('tbr', 0) > best_audio.get('tbr', 0)):
            if f.get('vcodec') == 'none' or not f.get('vcodec'):  # Audio only
                best_audio = f
        
        # Collect video-only formats with decent quality
        if (f.get('vcodec') != 'none' and f.get('vcodec') is not None and
            (f.get('acodec') == 'none' or not f.get('acodec')) and
            f.get('width', 0) >= 640):  # Only videos with width >= 640px
            video_formats.append(f)
    
    # Add combined format options with best audio + each video option
    if best_audio:
        for vf in video_formats:
            resolution = vf.get('resolution') or f"{vf.get('width')}x{vf.get('height')}"
            format_entry = {
                'format_id': f"{vf['format_id']}+{best_audio['format_id']}",
                'ext': vf.get('ext', 'mp4'),
                'resolution': resolution,
                'filesize': (vf.get('filesize', 0) or 0) + (best_audio.get('filesize', 0) or 0),
                'format_note': f"High Quality {resolution}",
                'vcodec': vf.get('vcodec'),
                'acodec': best_audio.get('acodec'),
                'has_video': True,
                'has_audio': True,
            }
            formats.append(format_entry)

    return jsonify({
        'title': info.get('title'),
        'uploader': info.get('uploader'),
        'thumbnail': info.get('thumbnail'),
        'duration': info.get('duration'),
        'formats': formats,
    })

@socketio.on('start_download')
def handle_download(data):
    url = data.get('url')
    format_id = data.get('format_id')
    if not url or not format_id:
        socketio.emit('error', {'message': 'Missing URL or format_id'})
        return

    def progress_hook(d):
        # Process and enhance the progress data for better display
        status = d.get('status', '')
        
        print(f"Progress hook received: status={status}")
        
        # Process the data based on status type
        if status == 'downloading':
            # Regular download progress
            progress_data = {
                'status': 'downloading',
                'downloaded_bytes': d.get('downloaded_bytes', 0),
                'total_bytes': d.get('total_bytes') or d.get('total_bytes_estimate', 0),
                'filename': d.get('filename', ''),
                'speed': d.get('speed', 0),
                'eta': d.get('eta', 0),
                'elapsed': d.get('elapsed', 0)
            }
            
            # Calculate percentage if possible
            if progress_data['total_bytes'] > 0:
                progress_data['percent'] = (progress_data['downloaded_bytes'] / progress_data['total_bytes']) * 100
                print(f"Download progress: {progress_data['percent']:.1f}%, "
                      f"{progress_data['downloaded_bytes']}/{progress_data['total_bytes']} bytes")
            else:
                progress_data['percent'] = 0
                print(f"Download progress: unknown percentage, "
                      f"{progress_data['downloaded_bytes']} bytes downloaded")
                
            socketio.emit('progress', progress_data)
        
        elif status == 'finished':
            # Download finished, now processing
            print("Download finished, starting FFmpeg processing")
            socketio.emit('progress', {
                'status': 'processing',
                'filename': d.get('filename', ''),
                'percent': 99.0,  # Not quite 100% as processing is still ongoing
                'message': 'Download complete, now processing with FFmpeg...'
            })
        
        elif status == 'error':
            # Error occurred
            print(f"Error during download: {d.get('error', 'Unknown error')}")
            socketio.emit('error', {'message': d.get('error', 'Download error occurred')})
        
        else:
            # For any other status, just send the data as is
            print(f"Other status received: {status}")
            socketio.emit('progress', d)

    ydl_opts = {
        'format': format_id,
        'progress_hooks': [progress_hook],
        'outtmpl': '%(title)s.%(ext)s',
        'postprocessors': [
            {'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'},  # Convert to MP4 if not already
            {'key': 'FFmpegFixupM4a'},  # Fix any audio issues
            {'key': 'FFmpegMetadata'}   # Add metadata
        ],
        'prefer_ffmpeg': True,
        'keepvideo': False,  # Delete the separate video file after merging
        'merge_output_format': 'mp4'  # Force merging to MP4 format
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("Download and processing complete!")
        # Send the final 100% complete message
        socketio.emit('progress', {
            'status': 'complete',
            'percent': 100.0,
            'message': 'Download and processing complete!'
        })
        socketio.emit('done', {'status': 'complete'})
    except Exception as e:
        print(f"Error during download: {str(e)}")
        socketio.emit('error', {'message': str(e)})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)

