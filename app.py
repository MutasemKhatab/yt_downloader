# Termux Backend (Python) - Flask + Flask-SocketIO + yt-dlp
# Save this as app.py in Termux

from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from yt_dlp import YoutubeDL
import eventlet

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

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
    for f in info.get('formats', []):
        resolution = f.get('resolution') or f"{f.get('width')}x{f.get('height')}"
        # TODO these 2 lines return only one resolution, need to fix
        if f.get('acodec') == 'none' or not f.get('acodec'):
            continue  # Skip formats without audio codec
        if f.get('vcodec') == 'none' or not f.get('vcodec'):
            continue
        format_entry = {
            'format_id': f['format_id'],
            'ext': f['ext'],
            'resolution': resolution,
            'filesize': f.get('filesize'),
            'format_note': f.get('format_note'),
            'vcodec': f.get('vcodec'),
            'acodec': f.get('acodec'),
            'has_video': f.get('vcodec') != 'none',
            'has_audio': f.get('acodec') != 'none',
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
        socketio.emit('progress', d)

    ydl_opts = {
        'format': format_id,
        'progress_hooks': [progress_hook],
        'outtmpl': '%(title)s.%(ext)s'
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        socketio.emit('done', {'status': 'complete'})
    except Exception as e:
        socketio.emit('error', {'message': str(e)})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)

