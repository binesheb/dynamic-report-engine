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

## Automatic updates

Do not enable unattended automatic deployment yet. The application stores encrypted external database credentials and can run against production PostgreSQL, MySQL, and SQL Server instances. Automatic replacement should only be added after a versioned release channel, health checks, and deployment rollback validation are established.
