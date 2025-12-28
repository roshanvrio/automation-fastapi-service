from app.database.connection import engine, Base
from app.models.models import ProcessTransaction

def create_tables():
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✓ Tables created successfully!")
        print(f"✓ Table 'process_transactions' is now in DashboardDB")
        
    except Exception as e:
        print(f"✗ Error creating tables: {e}")

if __name__ == "__main__":
    create_tables()