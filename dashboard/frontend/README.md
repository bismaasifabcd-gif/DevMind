# SWE Agent UI (React + Vite)

Professional single-page React UI scaffold for the Autonomous SWE Agent.

## Quick start

1. Install Node.js (v18+ recommended).
2. From this folder install dependencies:

```bash
cd dashboard/frontend
npm install
```

3. Create an env file with the backend base URL (default `http://localhost:8000`):

```bash
# .env
VITE_API_URL=http://localhost:8000
```

4. Run the dev server:

```bash
npm run dev
```

5. Open the app at `http://localhost:5173` and provide a local repo path and optional hints.

Notes:
- Backend CORS: If the frontend cannot call the backend, either add CORS support to the FastAPI server or set `VITE_API_URL` to the backend address.
- This scaffold does not yet implement real-time traces or MLflow browsing — next steps will wire those into the right-hand observability pane.
