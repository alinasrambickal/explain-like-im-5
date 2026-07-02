# Explain Like I'm 5: Chrome Extension

Highlight any text on a webpage → get a simple explanation powered by your choice of AI model.

## Project Structure

```
eli5/
├── extension/               # Chrome extension (frontend)
│   ├── manifest.json        # Extension config, permissions
│   ├── content/
│   │   └── content.js       # Injected into pages — grabs highlight + context
│   ├── popup/
│   │   ├── popup.html       # Extension popup UI
│   │   ├── popup.js         # Popup logic — talks to content.js + backend
│   │   └── popup.css        # Popup styles
│   └── icons/               # Extension icons (16, 48, 128px)
│
└── backend/                 # FastAPI backend (Python)
    ├── main.py              # App entrypoint, CORS, routes
    ├── routers/
    │   └── explain.py       # POST /explain endpoint
    ├── services/
    │   ├── gemini.py        # Gemini Flash handler
    │   ├── claude.py        # Claude Haiku handler
    │   └── groq.py          # Groq/Llama handler
    ├── middleware/
    │   └── rate_limit.py    # Global daily call counter
    ├── .env.example         # API key template (never commit .env)
    ├── requirements.txt
    └── .gitignore
```

## Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your API keys
uvicorn main:app --reload
```

### Extension
1. Open Chrome → `chrome://extensions`
2. Enable Developer Mode
3. Click "Load unpacked" → select the `extension/` folder
4. Pin the extension to your toolbar

## Usage
1. Highlight any text on a webpage (under 500 words)
2. Click the ELI5 extension icon
3. Pick your model, hit Explain
