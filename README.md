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
# Local development only; production must provide REPORTFORGE_SECRET_KEY.
export REPORTFORGE_ENV=development
docker compose up --build
```

Open `http://localhost:8000`.

## Production security

The application defaults to production mode and refuses to start without a valid `REPORTFORGE_SECRET_KEY`. Generate a URL-safe Fernet key once with `python -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'`, store it in your deployment secret manager, and keep the same key across restarts. Do not regenerate it after external database passwords have been encrypted. The deterministic development key is available only when `REPORTFORGE_ENV=development` is explicitly set; never use that mode with production data.

For the controlled manual update and rollback procedure, see `UPDATE.md`. Unattended updates are intentionally not enabled while the application is still maturing its release and rollback channel.
