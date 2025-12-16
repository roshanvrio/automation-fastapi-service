# create_tables.py
from app.db import engine
from app.models import Base

print("Creating tables in DB...")
Base.metadata.create_all(bind=engine)
print("Done.")
