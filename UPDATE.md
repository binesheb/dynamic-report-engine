# Updating Dynamic Report Engine

This application is deployed with Docker Compose. Use the manual update path below so every update can be checked and rolled back safely.

## Safe manual update

```bash
git status --short
git fetch origin
git checkout main
git pull --ff-only origin main
docker compose build --pull
docker compose up -d --wait
```

Before updating, make sure `git status --short` is empty. `git pull --ff-only` refuses history rewrites or merge commits, and `docker compose up -d --wait` verifies that Compose can bring the stack up before the update is accepted.

## Rollback

Record the currently running commit before updating:

```bash
git rev-parse HEAD
```

If the new version fails after deployment, return to the recorded commit and rebuild:

```bash
git checkout <known-good-commit>
docker compose build --pull
docker compose up -d --wait
```

## Legacy encrypted connection credentials

Older versions used a fixed, source-controlled Fernet fallback whenever `REPORTFORGE_SECRET_KEY` was not set. The production startup path in this change intentionally refuses to use that fallback. Passwords saved by an older deployment while the variable was unset will not decrypt with a newly configured key.

Before upgrading an installation that may have used the fallback:

1. Stop the service and make a restricted backup of the database before changing keys:
   ```bash
   docker compose down
   umask 077
   cp -p data/reportforge.db data/reportforge.db.pre-key-migration.bak
   ```
2. If the old deployment already used a configured `REPORTFORGE_SECRET_KEY`, retain that exact key; do not replace it. If it relied on the built-in fallback, treat the stored external database passwords as exposed and rotate them at the database servers.
3. For fallback-encrypted rows, remove the affected saved connection entries and recreate them with the rotated credentials after the updated service starts. Reassign reports to the new connection records and test each report before returning the service to users. If the records cannot be recreated and verified safely, stop the deployment and prepare a controlled offline migration instead.
4. Configure a persistent `REPORTFORGE_SECRET_KEY` in the deployment secret manager and keep it stable across restarts. Use `REPORTFORGE_ENV=production` (or leave it unset, since production is the default). Never set `REPORTFORGE_ENV=development` in production.
5. Keep the backup access-restricted until the migration and report checks are complete, then dispose of it under the data-retention policy. Never print or commit key material or database passwords.

Do not assume that setting a new key will decrypt rows written with the old fallback.

## Automatic updates

Do not enable unattended automatic deployment yet. The application stores encrypted external database credentials and can run against production PostgreSQL, MySQL, and SQL Server instances. Automatic replacement should only be added after a versioned release channel, health checks, and deployment rollback validation are established.
