# ⚡ Spotify Speed Ripper (V4.2 Universal)

A high-performance, concurrent downloader that rips audio from Spotify and YouTube at maximum bandwidth.

## 🚀 Features
- **Universal Engine:** Accepts Spotify Playlists, YouTube Links, and YouTube Mixes.
- **Concurrent Threading:** Downloads 15+ songs simultaneously (Fast AF).
- **Auto-Tagging:** Embeds Cover Art, Artist, and Title metadata into MP3s.
- **Deduplication:** Smartly ignores duplicate songs in infinite mixes.
- **Crash Proof:** "Paranoid Mode" skips deleted videos without stopping the queue.
- **Zero-Waste:** Auto-deletes zip files from the server after you download them.

## 🛠️ Tech Stack
- **Frontend:** React + Vite + TailwindCSS (Cyberpunk UI)
- **Backend:** Python FastAPI + yt-dlp
- **Accelerators:** FFmpeg (Conversion) + Aria2c (Multi-connection downloading)

## ⚡ How to Run
1. Clone the repo.
2. Add `ffmpeg.exe` and `aria2c.exe` to the `backend/` folder.
3. Create a `.env` file in `backend/` with your Spotify Credentials.
4. Run `launch.bat`.

## ⚠️ Disclaimer
For educational purposes only. Respect copyright laws.