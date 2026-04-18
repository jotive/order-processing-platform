# Alembic migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

Migration files live in `alembic/versions/`. Target DB URL comes from `settings.database_url` (see `app/core/config.py`), not the inline `alembic.ini` setting.
