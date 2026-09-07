from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here so Alembic can detect them
from app.models import patient, queue_ticket, reception  # noqa: F401, E402
