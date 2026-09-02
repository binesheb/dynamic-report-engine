# Dynamic Report Engine

A fully dynamic, database-driven SQL reporting platform.

## Features
- Unlimited nested menus
- Dynamic reports configured from Settings
- SQL editor and query testing
- Responsive animated UI
- Read-only SQL validation
- Dynamic result tables
- GitHub update checking
- Docker deployment

## Start

```bash
docker compose up --build
```

Open `http://localhost:8000`.

## Production security

Set a strong, persistent `REPORTFORGE_SECRET_KEY` in the deployment environment before storing external database credentials. If it is not set, the application falls back to a development key; that fallback must not be used for production data.

For the controlled manual update and rollback procedure, see `UPDATE.md`. Unattended updates are intentionally not enabled while the application is still maturing its release and rollback channel.
