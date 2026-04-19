## AdaptTutor (Step 1 scaffold)

This repo currently implements **Step 1 only** from `AdaptTutor_PRD.md`:

- Floating **launcher circle** (bottom-right, always-on-top)
- **Window watcher** thread (polls active window title every 3 seconds)
- **Menu UI** (slide-up list of feature buttons; no feature functionality yet)

### Run

```powershell  
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m adapttutor.main
```

### Notes

- The menu items are present for UI/UX validation only; they don’t do anything yet.
- The watcher uses `pygetwindow` to read the active window title and applies the keyword list from the PRD to compute a `study_mode` boolean.

