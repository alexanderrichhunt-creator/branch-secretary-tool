# Branch Executive Secretary Tool

A simple, secure website for tracking:
- Sacrament meeting talks (speaker + topic + date)
- A calendar view of talks and interviews
- Interview scheduling
- Temple recommend expiration dates and Protecting Children & Youth training due dates (manual entry)

## Quick start (local)

1. Open a terminal in this folder.
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

3. Create a `.env` file based on `.env.example`.
4. Run the app:

```bash
python run.py
```

Then open `http://127.0.0.1:5000`.

## Notes about Church data

This app does **not** connect to Church membership systems (LCR / Church Account data). Those systems contain sensitive records and generally do not provide an approved public API for custom apps. This tool is designed for **manual entry** or **importing a CSV you are authorized to export**.
