from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# SQLite database file
DATABASE_URL = "sqlite:///./blog.db"  # This will create a file named 'blog.db'

# Connect to the SQLite database
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Metadata and Base for SQLAlchemy models
metadata = MetaData()
Base = declarative_base()
