import yt_dlp

def check_formats(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    
    print(f'Total formats: {len(info.get("formats", []))}')
    
    # Find formats with both audio and video
    formats_with_audio_video = [
        f for f in info.get('formats', [])
        if f.get('acodec') != 'none' and f.get('acodec') is not None and 
           f.get('vcodec') != 'none' and f.get('vcodec') is not None
    ]
    
    print(f'Formats with audio and video: {len(formats_with_audio_video)}')
    print('Format IDs with both audio and video:')
    
    for f in formats_with_audio_video:
        resolution = f.get('resolution') or f"{f.get('width', '?')}x{f.get('height', '?')}"
        print(f"ID: {f['format_id']}, Format: {f.get('format', 'unknown')}, Resolution: {resolution}")

if __name__ == "__main__":
    check_formats('https://www.youtube.com/watch?v=Rd7yyutb-DI')
