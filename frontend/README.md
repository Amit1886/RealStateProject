# Unified Frontend (React + Tailwind)

Single React app for all modes:

- POS Embedded
- Tablet
- Mobile
- Desktop
- Admin Super Control

## Run

```bash
cd frontend
npm install
npm run dev
```

## Mode API dependencies

Backend endpoints used:

- `GET /api/current-mode/`
- `GET /api/system-mode/`
- `POST /api/change-mode/`

WebSocket:

- `/ws/system-mode/`
- `/ws/realtime/system_mode/`
