# App Lunch

`App Lunch` is a local launcher app:

- React gives you the UI.
- Python reads the apps installed on the current computer.
- Pressing Enter sends the app name to the backend and the backend opens the matching system app.

## Important hosting note

If you want to open apps from a user's computer, the backend must run on that same computer.

Normal web hosting platforms such as Netlify, Vercel, Render, or a shared VPS can host your React site, but they cannot open apps on a visitor's laptop. They only have access to their own server.

For this use case, the best options are:

1. Run React + Python locally on each machine.
2. Package the project as a desktop app later with Electron or Tauri, while keeping Python as the local system-access layer.
3. If many users need it, host only the UI centrally and install a small Python agent on every client machine. That agent is the part that reads installed apps and launches them.

## How installed apps are discovered

- Windows: `Get-StartApps` via PowerShell
- Linux: `.desktop` launchers from locations like `/usr/share/applications` and `~/.local/share/applications`
- macOS: `.app` bundles from `/Applications` and `~/Applications`

## Project structure

```text
backend/
  main.py
  requirements.txt
frontend/
  package.json
  public/index.html
  src/App.js
  src/index.js
  src/styles.css
```

## Run locally

### 1. Start the Python backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn main:app --reload
```

The backend starts on `http://127.0.0.1:8000`.

If `python3 -m venv .venv` fails on Debian/Ubuntu with an `ensurepip` error, install the OS package first:

```bash
sudo apt install python3.12-venv
```

### 2. Start the React frontend

```bash
cd frontend
npm install
npm start
```

The frontend starts on `http://localhost:3000`.

## How it works

1. The frontend loads the installed app list from `GET /apps`.
2. The user types an app name and presses Enter.
3. The frontend sends `POST /launch` with the typed name.
4. The backend finds the closest matching installed app and opens it.

## Example ideas to improve it

- Add app icons
- Add voice input
- Save recent apps
- Add exact-match and fuzzy-match modes
- Show categories like browser, editor, media, system tools
- Package it as a single installer with PyInstaller and Electron/Tauri
