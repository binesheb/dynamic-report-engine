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

The pre-change source had a fallback path when `REPORTFORGE_SECRET_KEY` was unset. Code inspection shows that path base64-encoded a 37-byte literal, while Fernet requires a URL-safe base64 key that decodes to exactly 32 bytes. The old no-key path therefore raises during `Fernet(...)` initialization before the application starts; it cannot have encrypted connection rows through the normal startup path.

Do not assume existing `password_enc` rows were created with that fallback, and do not rotate keys or delete saved connections solely on that assumption. Establish which valid key was actually used by the historical deployment before changing anything:

1. Preserve a restricted database backup before any migration:
   ```bash
   docker compose down
   umask 077
   cp -p data/reportforge.db data/reportforge.db.pre-key-migration.bak
   ```
2. If the deployment used a valid configured `REPORTFORGE_SECRET_KEY`, retain that exact key. Do not replace it merely as part of this upgrade.
3. Only if deployment evidence shows that existing rows were encrypted with a different valid key, prepare a controlled offline re-encryption or recreate the affected connections with rotated credentials. Test the migration against a restricted backup first; if the key history or row provenance is uncertain, stop and resolve that before modifying production data.
4. Configure a persistent `REPORTFORGE_SECRET_KEY` in the deployment secret manager and keep it stable across restarts. Use `REPORTFORGE_ENV=production` (or leave it unset, since production is the default). Never set `REPORTFORGE_ENV=development` in production.
5. Verify every saved connection and dependent report before returning the service to users. Keep backups access-restricted and never print or commit key material or database passwords.

Never infer the encryption key from the presence of database rows, and never log key material while checking deployment history.

## Automatic updates

Do not enable unattended automatic deployment yet. The application stores encrypted external database credentials and can run against production PostgreSQL, MySQL, and SQL Server instances. Automatic replacement should only be added after a versioned release channel, health checks, and deployment rollback validation are established.
