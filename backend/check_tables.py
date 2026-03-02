import sys
import os
from sqlalchemy import inspect

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.database import engine
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from app.database import engine

def list_tables():
    print("Checking database tables...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if not tables:
        print("No tables found in the database.")
    else:
        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"- {table}")
            
            # Optional: Print columns for each table
            # columns = inspector.get_columns(table)
            # print(f"  Columns: {', '.join([col['name'] for col in columns])}")

if __name__ == "__main__":
    list_tables()