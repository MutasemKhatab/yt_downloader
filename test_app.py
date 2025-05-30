import socketio
import time

sio = socketio.Client()

@sio.event
def connect():
    print("Connected to server")

@sio.event
def progress(data):
    print(f"Progress: {data}")

@sio.event
def done(data):
    print("Download completed:", data)
    sio.disconnect()

@sio.event
def error(data):
    print("Error:", data)
    sio.disconnect()

@sio.event
def disconnect():
    print("Disconnected from server")

def main():
    sio.connect('http://127.0.0.1:5000')
    url = 'https://www.youtube.com/watch?v=TEZdqFXlVh0'  # replace with your video URL
    format_id = '18'  # replace with desired format_id from /info endpoint
    print("Starting download...")
    sio.emit('start_download', {'url': url, 'format_id': format_id})
    # Keep script running to listen for events
    while sio.connected:
        time.sleep(1)

if __name__ == '__main__':
    main()

