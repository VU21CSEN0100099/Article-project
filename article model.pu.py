from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Blog(Base):
    __tablename__ = "blogs"  # The table name in the database

    id = Column(Integer, primary_key=True, index=True)  # Blog ID
    title = Column(String, index=True)  # Blog title
    content = Column(Text)  # Blog content
    date = Column(DateTime)  # Blog date
    author = Column(String)  # Blog author
    comments = Column(Text)  # Blog comments
