# 360 Game Hall Auto Start

## 1. Quick start

Run this in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File E:\auto360\start_naruto_ol.ps1
```

The script will:

- Start `E:\360Game5\bin\360Game.exe`
- Try `Ctrl+F` and search `Naruto OL`
- Press Enter to open the first result

## 2. If hotkey search does not work

Run the coordinate helper first:

```powershell
powershell -ExecutionPolicy Bypass -File E:\auto360\capture_point.ps1
```

Move the mouse to each target and note the coordinates:

- Search box
- First search result
- Play button

Then run the launcher with coordinates:

```powershell
powershell -ExecutionPolicy Bypass -File E:\auto360\start_naruto_ol.ps1 `
  -SkipSearchHotkey `
  -SearchBoxX 1180 -SearchBoxY 110 `
  -FirstResultX 960 -FirstResultY 260 `
  -PlayButtonX 1320 -PlayButtonY 820
```

## 3. Useful parameters

- `-GameName`: default is `Naruto OL`
- `-LaunchWaitSeconds`: wait time after launcher start
- `-SearchResultWaitSeconds`: wait time for the search result page
- `-PostResultWaitSeconds`: wait time after opening the result

## 4. Notes

- Avoid switching windows while the script is running, or keystrokes may go to another app.
- If 360 Game Hall shows login, update, or popup dialogs, dismiss them once manually before using the script.
- Game Hall UI changes over time, so coordinate mode is the safest fallback.
