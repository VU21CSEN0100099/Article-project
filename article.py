from email import message
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional,List
from sqlalchemy import MetaData, create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
import redis

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

#create a redis client

# Connect to Redis running on localhost:6379 (Docker mapped port)
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Test Redis connection
try:
    redis_client.set("test_key", "Hello Redis!")
    value = redis_client.get("test_key")
    print(f"Connected to Redis! Retrieved value: {value}")
except redis.ConnectionError:
    print("Failed to connect to Redis.")




DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
metadata = MetaData()


Base = declarative_base()



SECRET_KEY = "my_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token expiration time

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

class BlogModel(Base):
    __tablename__ = "blogs"  # The table name in the database

    id = Column(Integer, primary_key=True, index=True)  # Blog ID
    title = Column(String, index=True)  # Blog title
    username= Column(String, unique=True, index=True)
    password= Column(String)
    content = Column(Text)  # Blog content
    date = Column(DateTime)  # Blog date
    author = Column(String)  # Blog author
    comments = Column(Text)  # Blog comments


Base = declarative_base()


# Create all tables in the database
Base.metadata.create_all(bind=engine)




app=FastAPI()

blogs={}

class Blog(BaseModel):
    title: str
    content: str
    date: datetime
    comments: list
    author: str


class optionalBlog(BaseModel):
    title:Optional[str]=None
    content: Optional[str]=None
    date: Optional[datetime]=None
    comments: Optional[str]=None
    author:Optional[str]=None

# dependency session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/register/")
def register(username: str, password: str, db: Session = Depends(get_db)):
    hashed_password = hash_password(password)
    db_user = db.query(BlogModel).filter(BlogModel.username == username).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    new_user = BlogModel(username=username, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully"}

@app.post("/token")
def login_for_access_token(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(BlogModel).filter(BlogModel.username == username).first()
    if user is not verify_password(password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
def read_users_me(token: str = Depends(oauth2_scheme)):
    user_data = verify_token(token)
    if user_data is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"username": user_data.get("sub")}



@app.post("/create-blog/")
def create_blog(blog_id: int, blog: Blog, db: Session = Depends(get_db)):
    if blog_id in blogs:
        raise HTTPException(status_code=404, detail="blog already exists/invalid blog id")
    blogs[blog_id] = blog
    db_blog = BlogModel(id=blog_id, title=blog.title, content=blog.content, date=blog.date, comments=blog.comments, author=blog.author)
    db.add(db_blog)
    db.commit()
    db.refresh(db_blog)
    return db_blog


@app.get("/get-blog/")
def get_blog(blog_id: int, db: Session = Depends(get_db)):

        # Check if blog is in Redis cache
    cached_blog = redis_client.get(f"blog:{blog_id}")
    if cached_blog:
        return {"blog": eval(cached_blog)}  
        #if not in the cache, get from the database
    db_blog = db.query(BlogModel).filter(BlogModel.id == blog_id).first()
    if db_blog is None:
        raise HTTPException(status_code=404, detail="blog not found")

    #expire the cache in 5 mins
    redis_client.setex(f"blog:{blog_id}", 300, str(db_blog.__dict__))

    return db_blog


@app.put("/put-blog/")
def put_blog(blog_id: int, blog: optionalBlog, db: Session = Depends(get_db)):
    db_blog = db.query(BlogModel).filter(BlogModel.id == blog_id).first()
    if db_blog is None:
        raise HTTPException(status_code=404, detail="blog not found")
    if blog.title is not None:
        db_blog.title = blog.title
    if blog.content is not None:
        db_blog.content = blog.content
    if blog.date is not None:
        db_blog.date = blog.date
    if blog.comments is not None:
        db_blog.comments = blog.comments
    if blog.author is not None:
        db_blog.author = blog.author
    db.commit()
    db.refresh(db_blog)


    # Update the Redis cache with the latest blog data
    redis_client.setex(f"blog:{blog_id}", 300, str(db_blog.__dict__))  


    return db_blog


@app.delete("/delete-blog/")
def delete_blog(blog_id: int, db: Session = Depends(get_db)):
    db_blog = db.query(BlogModel).filter(BlogModel.id == blog_id).first()
    if db_blog is None:
        raise HTTPException(status_code=404, detail="blog not found")
    db.delete(db_blog)
    db.flush()
    db.commit()

    # Remove from cache
    redis_client.delete(f"blog:{blog_id}")


    return {"message": "blog is deleted"}