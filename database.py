from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

DB_USER = "root"
DB_PASSWORD = "Aryan%4054321"
DB_HOST = "localhost"
DB_NAME = "company_data"

DATABASE_URL = "mysql+mysqlconnector://root:Aryan%4054321@localhost/company_data"

engine = create_engine(DATABASE_URL)
metadata = MetaData()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
