# Windows setup

1. Install Python **3.12 64-bit** with the Python launcher enabled.
2. Extract the ZIP completely. Do not run the project from inside the ZIP preview.
3. Open the extracted `aerial-robotics-platform` folder.
4. Run `start-windows.bat`.
5. Open `http://127.0.0.1:8000` in Chrome or Edge.

The first run downloads dependencies. The window stays open while the backend runs. No Node.js, GPU, drone, camera, API key or paid map account is required for the bundled simulation.

If you see `No suitable Python runtime found`, run `py -0p` in PowerShell and confirm Python 3.12 exists. The launcher deliberately selects 3.12 instead of an unrelated Python 3.14 installation.

If port 8000 is occupied, use:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001
```

Then open `http://127.0.0.1:8001`. The built frontend uses the same origin automatically.

To edit the frontend, install Node.js 22 LTS, open `frontend` in a terminal, run `npm ci`, and then `npm run dev`. The development server expects the backend on port 8000. Use `npm run build` after editing to refresh the Python-served dashboard.
