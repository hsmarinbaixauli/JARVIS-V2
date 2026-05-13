# Jarvis V2 - Web Chat ERP Assistant

## Project Overview
Jarvis V2 is a web chat application for working with business and ERP workflows from a browser. Users interact through a React chat interface. The FastAPI backend owns conversation orchestration, authentication boundaries, tool routing, and persistence. ERP actions that require browser automation are handled by a Playwright-based agent.

The old Windows voice-assistant launcher and autostart flow have been removed. Treat Jarvis V2 as a browser-first product.

## Architecture
- React frontend: chat UI, session state, message streaming, file/input controls, and user-visible workflow status.
- FastAPI backend: HTTP/WebSocket API, request validation, conversation orchestration, LLM calls, tool dispatch, and service integrations.
- Playwright ERP agent: browser automation layer for ERP login, navigation, data extraction, form filling, and task confirmation.
- Shared configuration: environment variables only; secrets stay out of source control.
- Tests: backend unit/integration tests, frontend component tests, and Playwright automation checks for ERP flows.

## Primary Runtime Flow
1. User sends a message from the React chat interface.
2. Frontend calls the FastAPI chat endpoint or opens a streaming connection.
3. Backend normalizes the request, appends conversation context, and routes intent to the LLM and available tools.
4. If the task needs ERP interaction, the backend delegates a bounded job to the Playwright ERP agent.
5. The ERP agent reports structured progress and results back to the backend.
6. Backend returns the final answer, tool traces, and any required confirmation prompts to the frontend.

## Expected Project Areas
- `frontend/` - React application and chat components.
- `backend/` - FastAPI app, routers, schemas, services, and orchestration code.
- `agents/erp_playwright/` - Playwright ERP automation tasks and browser/session utilities.
- `tests/` - backend tests plus ERP automation tests where practical.
- `.env` / `.env.example` - local configuration template and secrets.

## Commands
Use the commands that match the files present in the current checkout:
- Backend setup: create a Python virtual environment and install `requirements.txt`.
- Backend run: `uvicorn backend.main:app --reload` when the FastAPI app is present.
- Frontend setup: `npm install` from `frontend/`.
- Frontend run: `npm run dev` from `frontend/`.
- ERP agent tests: `npx playwright test` from the package that owns Playwright tests.
- Python tests: `pytest`.

## Code Style
- Python: type hints, Pydantic models for API boundaries, small FastAPI routers, explicit service classes/functions.
- TypeScript/React: typed props, local component state where possible, clear API client boundaries, accessible controls.
- Playwright: stable selectors, explicit waits for app state, reusable login/session helpers, no arbitrary sleeps unless documented.
- Use English names for code, comments, routes, and schemas.
- Keep comments short and useful; prefer readable code over narration.

## Critical Constraints
- Never hardcode credentials, ERP passwords, API keys, or tenant URLs.
- Keep `.env` local and out of commits.
- Store browser session state only in approved local credential/cache paths.
- ERP write actions must be explicit, auditable, and confirmable before submission when there is user impact.
- Do not reintroduce Windows autostart or voice launcher files unless the product direction changes.

## Available Agents
- agents-orchestrator - coordinate multi-agent implementation or investigation.
- planner - plan features before implementation.
- architect - system design decisions.
- code-reviewer - review behavioral risk, regressions, and missing tests.
- python-reviewer - Python and FastAPI review.
- security-reviewer - check credential handling and automation safety.
- tdd-guide - test-driven development.
- build-error-resolver - fix dependency, build, and runtime issues.
- engineering-frontend-developer - React UI implementation.
- testing-evidence-collector - gather verification evidence.

## Working Notes
- Prefer small, vertical slices: API contract, backend behavior, frontend integration, then ERP automation.
- Keep ERP automation behind backend-owned interfaces so the UI never depends on browser automation details.
- When updating docs, keep them aligned with the web chat architecture rather than the legacy voice assistant.
