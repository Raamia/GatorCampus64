"""python -m sgl_api.schema : apply schema.sql to $DATABASE_URL (idempotent)."""
from . import config, db

if __name__ == "__main__":
    db.apply_schema(config.load().database_url)
    print("schema applied")
