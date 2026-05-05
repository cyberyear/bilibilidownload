# Bilibili Downloader

## Start (Windows)

Install dependencies:

```powershell
py -3.11 -m pip install -r E:\auto360\requirements.txt
```

Run the web app (Windows):

```powershell
powershell -ExecutionPolicy Bypass -File E:\auto360\run_app.ps1
```

Then open:

```text
http://localhost:8000
```

## Build Desktop EXE

Install dependencies and build:

```powershell
powershell -ExecutionPolicy Bypass -File E:\auto360\build_exe.ps1
```

After build, the executable will be here:

```text
E:\auto360\dist\BilibiliDownloader.exe
```

Double-clicking the EXE will start the local server and open the app in your default browser.

## What it does

- Search Bilibili videos by keyword
- Show search results in a simple frontend
- Download the selected video to a directory you choose
- Track job progress in the browser
- Optionally reuse cookies from Chrome, Edge, or Firefox for videos that need login state

## Notes

- The app uses Bilibili's web search API for search and `yt-dlp` for downloads.
- Some videos may fail without browser cookies, login, or a newer Bilibili-compatible extractor.
- `ffmpeg` is recommended for best audio/video merging quality.
- Download only videos you are authorized to save, and comply with copyright law and Bilibili's terms.
