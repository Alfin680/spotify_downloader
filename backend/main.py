import os
import shutil
import asyncio
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp

# --- CONFIGURATION ---
load_dotenv()

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 15))
# SAFETY CAP: Stop processing playlist after this many songs to prevent infinite mixes
MAX_PLAYLIST_ITEMS = 100 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("public_downloads", exist_ok=True)
app.mount("/public_downloads", StaticFiles(directory="public_downloads"), name="public_downloads")

auth_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)

def sanitize_filename(name):
    if not name:
        name = "Unknown_Track"
    cleaned = re.sub(r'[\\/*?:"<>|]', "", str(name))
    return cleaned.strip()

def cleanup_file(path: str):
    try:
        os.remove(path)
    except Exception as e:
        print(f"Error deleting file: {e}")

@app.get("/download_once/{filename}")
def download_and_delete(filename: str, background_tasks: BackgroundTasks):
    file_path = os.path.join("public_downloads", filename)
    if os.path.exists(file_path):
        background_tasks.add_task(cleanup_file, file_path)
        return FileResponse(file_path, filename=filename)
    return {"error": "File not found"}

# --- THE DOWNLOADER ---
def download_single_track(track_info, folder_path):
    track_name = track_info.get('name', 'Unknown Track')
    safe_song_name = sanitize_filename(track_name)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{folder_path}/{safe_song_name}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'writethumbnail': True,
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
            {'key': 'EmbedThumbnail'},
            {'key': 'FFmpegMetadata'},
        ],
        'external_downloader': 'aria2c',
        'external_downloader_args': ['-x', '16', '-s', '16', '-k', '1M'],
    }

    target = ""
    if track_info.get('url'):
        target = track_info['url']
    else:
        artist = track_info.get('artist', 'Unknown Artist')
        target = f"ytsearch1:{track_name} - {artist} audio"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([target])
        return True
    except Exception as e:
        print(f"Failed {track_name}: {e}")
        return False

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    temp_folder = ""
    
    try:
        data = await websocket.receive_json()
        url = data.get("url")
        clean_tracks = []
        seen_urls = set() # <--- DEDUPLICATION MEMORY
        playlist_name = "Music_Download"

        await websocket.send_json({"status": "ANALYZING LINK..."})

        # --- BRANCH A: SPOTIFY ---
        if "spotify.com" in url:
            try:
                playlist_data = sp.playlist(url)
                playlist_name = sanitize_filename(playlist_data.get('name', 'Spotify_Playlist'))
                results = sp.playlist_tracks(url)
                tracks = results['items']
                while results['next']:
                    results = sp.next(results)
                    tracks.extend(results['items'])
                
                # Deduplicate Spotify tracks based on Name+Artist
                for t in tracks:
                    if t['track']:
                        t_name = t['track']['name']
                        t_artist = t['track']['artists'][0]['name']
                        unique_key = f"{t_name}_{t_artist}"
                        
                        if unique_key not in seen_urls:
                            clean_tracks.append({'name': t_name, 'artist': t_artist})
                            seen_urls.add(unique_key)

            except Exception as e:
                print(f"Spotify Error: {e}")
                await websocket.send_json({"error": "INVALID SPOTIFY URL"})
                return

        # --- BRANCH B: YOUTUBE ---
        elif "youtube.com" in url or "youtu.be" in url:
            try:
                # PLAYLIST_END: CAP AT 100 SONGS
                ydl_opts_meta = {
                    'extract_flat': True, 
                    'quiet': True, 
                    'ignoreerrors': True,
                    'yes_playlist': True,
                    'playlistend': MAX_PLAYLIST_ITEMS # <--- STOPS INFINITE LOOPS
                }
                
                with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    if 'entries' in info:
                        playlist_name = sanitize_filename(info.get('title', 'YouTube_Playlist'))
                        
                        entries = list(info['entries'])
                        for entry in entries:
                            if entry and entry.get('url'):
                                # DEDUPLICATION: CHECK URL
                                if entry['url'] not in seen_urls:
                                    title = entry.get('title', f"Video_{entry.get('id', 'unknown')}")
                                    clean_tracks.append({'name': title, 'url': entry['url']})
                                    seen_urls.add(entry['url'])
                                
                    else:
                        playlist_name = sanitize_filename(info.get('title', 'YouTube_Video'))
                        title = info.get('title', 'Unknown_Video')
                        video_url = info.get('original_url', info.get('webpage_url', url))
                        clean_tracks = [{'name': title, 'url': video_url}]

            except Exception as e:
                print(f"YouTube Error: {e}")
                await websocket.send_json({"error": f"YT ERROR: {str(e)}"})
                return
        
        else:
             await websocket.send_json({"error": "LINK NOT SUPPORTED"})
             return

        if not clean_tracks:
            await websocket.send_json({"error": "NO DOWNLOADABLE SONGS FOUND"})
            return

        # --- DOWNLOADING ---
        unique_id = f"{int(time.time())}"
        temp_folder = f"temp_{unique_id}"
        os.makedirs(temp_folder, exist_ok=True)

        await websocket.send_json({"status": f"STARTING DOWNLOAD ({len(clean_tracks)} ITEMS)..."})
        
        loop = asyncio.get_event_loop()
        completed = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                loop.run_in_executor(executor, download_single_track, track, temp_folder)
                for track in clean_tracks
            ]
            
            for f in asyncio.as_completed(futures):
                await f
                completed += 1
                progress = int((completed / len(clean_tracks)) * 100)
                await websocket.send_json({"progress": progress, "status": f"PROCESSED: {completed}/{len(clean_tracks)}"})

        await websocket.send_json({"status": "PACKAGING FILES..."})
        
        zip_filename = f"{playlist_name}_{unique_id}.zip"
        zip_output_path = os.path.join("public_downloads", zip_filename)
        
        shutil.make_archive(zip_output_path.replace('.zip', ''), 'zip', temp_folder)
        shutil.rmtree(temp_folder)

        download_url = f"http://localhost:8000/download_once/{zip_filename}"
        
        await websocket.send_json({
            "status": "READY", 
            "download_url": download_url,
            "filename": zip_filename
        })

    except Exception as e:
        print(f"Critical Error: {e}")
        await websocket.send_json({"error": str(e)})
        if temp_folder and os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)