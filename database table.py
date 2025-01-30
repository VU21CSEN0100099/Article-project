from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# Create all tables in the database
Base.metadata.create_all(bind=engine)
