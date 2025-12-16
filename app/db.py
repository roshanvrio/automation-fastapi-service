# app/db.py
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv

load_dotenv()

driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
server = os.getenv("DB_SERVER", ".")
database = os.getenv("DB_DATABASE", "automationDashboard")
user = os.getenv("DB_USER", "sa")
password = os.getenv("DB_PASSWORD", "")
trust = os.getenv("DB_TRUST_CERT", "yes")

odbc_str = (
    f"DRIVER={{{driver}}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={user};"
    f"PWD={password};"
    f"TrustServerCertificate={trust};"
)
connection_url = "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_str)

# engine (fast_executemany helps with pandas bulk insert)
engine = create_engine(connection_url, fast_executemany=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))
