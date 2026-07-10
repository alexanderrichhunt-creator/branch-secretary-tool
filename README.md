# Branch Executive Secretary Tool

A simple, secure website for tracking:
- Sacrament meeting talks (speaker + topic + date)
- A calendar view of talks and interviews
- Interview scheduling
- Temple recommend expiration dates and Protecting Children & Youth training due dates (manual entry)
- Stream program export for OBS automation

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

## Stream API (OBS)

Machine-readable sacrament program for a given Sunday. Uses a dedicated API key
(not a human login), so a local OBS controller can pull speakers and hymns safely.

### Setup

1. Generate a long random key, for example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. Set `STREAM_API_KEY` in `.env` (local) or in the Render environment variables (production).
3. Redeploy / restart the app.

If `STREAM_API_KEY` is unset, the endpoint returns **503** and stays disabled.

### Endpoint

```http
GET /api/stream/program?date=YYYY-MM-DD
```

`date` is optional. When omitted, the next/current sacrament Sunday is used
(same rule as the bulletin builder).

### Auth (any one)

```http
Authorization: Bearer <STREAM_API_KEY>
```

```http
X-Stream-Api-Key: <STREAM_API_KEY>
```

```http
GET /api/stream/program?date=2026-07-12&api_key=<STREAM_API_KEY>
```

Prefer a header in production; the query param is mainly for quick tests.

### Example

```bash
curl -sS -H "Authorization: Bearer $STREAM_API_KEY" \
  "https://branch-secretary-tool.onrender.com/api/stream/program?date=2026-07-12"
```

### Response shape (schema_version 1)

```json
{
  "schema_version": 1,
  "date": "2026-07-12",
  "date_display": "July 12, 2026",
  "meeting": {
    "type": "sacrament",
    "speakers_mode": "talks",
    "is_special": false,
    "presiding": "...",
    "conducting": "...",
    "sacrament_notes": "..."
  },
  "hymns": {
    "opening": { "number": "6", "title": "...", "line": "#6  ...", "lyrics": null, "has_lyrics": false },
    "sacrament": { "...": "..." },
    "intermediate": null,
    "closing": { "...": "..." }
  },
  "speakers": [
    { "index": 1, "order": 1, "name": "Jane Doe", "calling": null, "topic": "Faith" }
  ],
  "stream_cues": [
    { "id": "opening_hymn", "label": "Opening hymn: ...", "scene_hint": "hymn" },
    { "id": "sacrament", "label": "Sacrament (pause live feed)", "scene_hint": "sacrament" },
    { "id": "speaker_1", "label": "Speaker 1: Jane Doe", "scene_hint": "speaker" },
    { "id": "intermission", "scene_hint": "intermission" },
    { "id": "sunday_school", "scene_hint": "sunday_school" }
  ],
  "bulletin_saved": true,
  "generated_at": "2026-07-12T14:00:00Z"
}
```

Data comes from the **bulletin draft** for that date (if saved), otherwise branch
bulletin defaults, plus **talks** assigned to that Sunday. Adult hymn **lyrics**
are only present when available in the app’s lyrics data (Children’s Songbook is
populated today; Hymns titles always resolve from `data/hymns.json`).

`calling` is reserved for a future field and is currently always `null`.

## Notes about Church data

This app does **not** connect to Church membership systems (LCR / Church Account data). Those systems contain sensitive records and generally do not provide an approved public API for custom apps. This tool is designed for **manual entry** or **importing a CSV you are authorized to export**.
