# Jarvis V2

Jarvis V2 is a browser-based AI chat application for ERP and business workflows. It combines a React chat frontend, a FastAPI backend, and a Playwright ERP agent that can operate the ERP web UI when an action cannot be completed through a direct API.

The legacy Windows voice assistant launchers and autostart scripts have been removed. Jarvis V2 is now a web app.

## What it does

- Chat with Jarvis from a React web interface.
- Stream or display assistant responses from a FastAPI backend.
- Route business tasks through backend services and LLM tool orchestration.
- Use a Playwright ERP agent for browser-based ERP navigation, extraction, and form workflows.
- Keep risky ERP actions confirmable and auditable before final submission.

## Architecture

```text
User
  |
  v
React frontend
  - chat interface
  - session state
  - progress/status rendering
  |
  v
FastAPI backend
  - chat endpoints
  - orchestration
  - tool routing
  - validation and persistence boundaries
  |
  v
Playwright ERP agent
  - authenticated browser session
  - ERP navigation
  - data extraction
  - form filling and confirmation
```

## Main components

- **Frontend**: React application for the chat experience and workflow status.
- **Backend**: FastAPI service that exposes the chat API, manages context, validates requests, and coordinates tools.
- **ERP agent**: Playwright automation worker for ERP tasks that require browser interaction.
- **Configuration**: `.env` for local secrets and environment-specific values.
- **Tests**: Python tests for backend behavior, frontend tests for UI behavior, and Playwright tests for ERP automation flows.

## Expected project structure

```text
Jarvis V2/
|-- backend/                 # FastAPI app, routers, schemas, services
|-- frontend/                # React app
|-- agents/
|   `-- erp_playwright/      # ERP browser automation agent
|-- tests/                   # Backend and integration tests
|-- credentials/             # Local credentials/session data, gitignored
|-- .env.example             # Configuration template
|-- requirements.txt         # Python dependencies
|-- CLAUDE.md                # Development guidance for agents
`-- README.md
```

Some checkouts may still contain older `src/voice`, `src/gmail`, `src/spotify`, or similar modules from the previous voice-assistant prototype. New work should target the web chat architecture above.

## Setup

### Backend

Create and activate a Python virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

When the FastAPI app is present, start it with:

```powershell
uvicorn backend.main:app --reload
```

### Frontend

From the frontend package:

```powershell
cd frontend
npm install
npm run dev
```

### Playwright ERP agent

Install browser dependencies from the package that owns the Playwright tests:

```powershell
npx playwright install
npx playwright test
```

## Configuration

Use `.env` for local configuration. Typical values include:

```env
ANTHROPIC_API_KEY=
ERP_BASE_URL=
ERP_USERNAME=
ERP_PASSWORD=
ERP_HEADLESS=true
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
```

Never commit real ERP credentials, API keys, browser storage state, or OAuth tokens.

## Development workflow

1. Define the user workflow in the React chat UI.
2. Add or update the FastAPI route/schema/service boundary.
3. Implement orchestration and tool calls in the backend.
4. Add a bounded Playwright ERP task only when browser automation is required.
5. Cover the change with focused backend, frontend, or Playwright tests.
6. Verify the full chat-to-ERP flow locally.

## Verification

Use the relevant checks for the area you changed:

```powershell
pytest
npm test
npx playwright test
```

## Author

Hugo
