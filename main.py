from typing import List
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

import mimetypes

from fastapi.responses import FileResponse





from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, File, Form
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

# ============================================================
# DATABASE
# ============================================================

DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)



# ============================================================
# DATABASE MIGRATION: ADD MISSING COLUMNS SAFELY
# ============================================================

with engine.begin() as connection:
    # Add the profile_pic column to existing users tables.
    user_columns = {
        row[1]
        for row in connection.execute(
            text("PRAGMA table_info(users)")
        )
    }

    if "profile_pic" not in user_columns:
        connection.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN profile_pic VARCHAR(500)"
            )
        )

    # Add the category column to existing content_items tables.
    content_columns = {
        row[1]
        for row in connection.execute(
            text("PRAGMA table_info(content_items)")
        )
    }

    if "category" not in content_columns:
        connection.execute(
            text(
                "ALTER TABLE content_items "
                "ADD COLUMN category VARCHAR(50) "
                "NOT NULL DEFAULT 'Other'"
            )
        )


# Enable SQLite foreign-key constraints, including CASCADE.
@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# DATABASE MODELS
# ============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    profile_pic = Column(String(500), nullable=True)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    author_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "post_id",
            name="unique_user_post_like",
        ),
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)

    category = Column(
        String(50),
        nullable=False,
        default="Other"
    )

    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), unique=True, nullable=False)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

class ContentLike(Base):
    __tablename__ = "content_likes"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    content_id = Column(
        Integer,
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "content_id",
            name="unique_user_content_like",
        ),
    )


class ContentComment(Base):
    __tablename__ = "content_comments"

    id = Column(Integer, primary_key=True, index=True)

    content = Column(Text, nullable=False)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    content_id = Column(
        Integer,
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

# Create all tables AFTER every model is defined.
Base.metadata.create_all(bind=engine)

CONTENT_CATEGORIES = [
    "Technology",
    "Science",
    "Business",
    "Mathematics",
    "Languages",
    "Other",
]
# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    profile_pic: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)




class UserUpdate(BaseModel):
    username: str
    email: str


class UserLogin(BaseModel):
    email: str
    password: str


class PostCreate(BaseModel):
    author_id: int
    content: str


class PostUpdate(BaseModel):
    content: str


class PostResponse(BaseModel):
    id: int
    author_id: int
    author_username: str
    content: str
    created_at: datetime
    likes_count: int = 0
    comments_count: int = 0


class CommentCreate(BaseModel):
    user_id: int
    content: str


class CommentResponse(BaseModel):
    id: int
    user_id: int
    username: str
    post_id: int
    content: str
    created_at: datetime


# ============================================================
# USER CRUD FUNCTIONS
# ============================================================

def create_user_db(db: Session, user: UserCreate):
    db_user = User(
        username=user.username,
        email=user.email,
        password=user.password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_users_db(db: Session):
    return db.query(User).all()


def get_user_db(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def update_user_db(db: Session, user_id: int, user: UserUpdate):
    db_user = get_user_db(db, user_id)

    if db_user is None:
        return None

    db_user.username = user.username
    db_user.email = user.email

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user_db(db: Session, user_id: int):
    db_user = get_user_db(db, user_id)

    if db_user is None:
        return None

    db.delete(db_user)
    db.commit()
    return db_user


# ============================================================
# FASTAPI APP AND CORS
# ============================================================

app = FastAPI(
    title="User API",
    description="FastAPI CRUD User API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "FastAPI User API is running"}


# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, user.email)

    if db_user is None or db_user.password != user.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    return {
        "message": "Login successful",
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
        },
    }






# ============================================================
# EDUCATIONAL CONTENT UPLOADS
# ============================================================

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_PIC_DIR = UPLOAD_DIR / "profile_pics"
PROFILE_PIC_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_PROFILE_PIC_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp"
}


@app.post("/users/{user_id}/profile-picture")
async def upload_profile_picture(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_PROFILE_PIC_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Use a JPG, PNG, or WebP profile picture",
        )

    stored_filename = f"{uuid4().hex}{extension}"
    file_path = PROFILE_PIC_DIR / stored_filename
    size = 0

    try:
        with file_path.open("wb") as output:
            while True:
                chunk = await file.read(64 * 1024)

                if not chunk:
                    break

                size += len(chunk)

                if size > 5 * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail="Profile picture must be 5 MB or smaller",
                    )

                output.write(chunk)

        if size == 0:
            raise HTTPException(
                status_code=400,
                detail="The image is empty",
            )

        old_profile_pic = user.profile_pic

        user.profile_pic = (
            f"/uploads/profile_pics/{stored_filename}"
        )

        db.commit()
        db.refresh(user)

        # Remove the previous image only if it belongs to this
        # application's profile-picture directory.
        if old_profile_pic:
            old_name = Path(old_profile_pic).name
            old_path = PROFILE_PIC_DIR / old_name

            if (
                old_name == old_profile_pic.split("/")[-1]
                and old_path != file_path
                and old_path.is_file()
            ):
                try:
                    old_path.unlink()
                except OSError:
                    pass

        return {
            "message": "Profile picture updated successfully",
            "user_id": user.id,
            "profile_pic": user.profile_pic,
        }

    except Exception:
        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise

    finally:
        await file.close()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".txt",
    ".jpg",
    ".jpeg",
    ".png",
    ".mp4",
}

# Allow uploaded files to be accessed by URL.
app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads",
)




@app.post("/content/upload", status_code=201)
async def upload_content(
    name: str = Form(...),
    category: str = Form("Other"),
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Validate the category.
    category = category.strip()

    if category not in CONTENT_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid category",
        )

    # Validate the content name.
    name = name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Content name is required",
        )

    if len(name) > 150:
        raise HTTPException(
            status_code=400,
            detail="Content name cannot exceed 150 characters",
        )

    # Check that the uploader exists.
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    # Validate the file extension.
    original_filename = Path(file.filename or "").name

    if not original_filename:
        raise HTTPException(
            status_code=400,
            detail="Please select a valid file",
        )

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="This file type is not supported",
        )

    # Generate a unique stored filename.
    stored_filename = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / stored_filename
    size = 0

    try:
        # Save the file in chunks, enforcing the 20 MB limit.
        with file_path.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                size += len(chunk)

                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds the 20 MB limit",
                    )

                output.write(chunk)

        if size == 0:
            raise HTTPException(
                status_code=400,
                detail="The selected file is empty",
            )

        # Save the resource and its category in SQLite.
        item = ContentItem(
            name=name,
            category=category,
            original_filename=original_filename,
            stored_filename=stored_filename,
            user_id=user_id,
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        return {
            "message": "Content uploaded successfully",
            "content": {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "original_filename": item.original_filename,
                "user_id": item.user_id,
                "created_at": item.created_at,
                "file_url": f"/uploads/{item.stored_filename}",
            },
        }

    except Exception:
        # Remove the file if uploading or saving fails.
        if file_path.exists():
            file_path.unlink()

        db.rollback()
        raise

    finally:
        await file.close()









# ============================================================
# SERVE EDUCATIONAL CONTENT FOR BROWSER PREVIEW
# ============================================================

@app.get("/content/{content_id}/preview")
def preview_educational_content(
    content_id: int,
    db: Session = Depends(get_db),
):
    item = (
        db.query(ContentItem)
        .filter(ContentItem.id == content_id)
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Educational content not found",
        )

    # Use the server-generated filename, never a client-supplied path.
    file_path = UPLOAD_DIR / item.stored_filename

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="The uploaded file could not be found",
        )

    extension = file_path.suffix.lower()

    preview_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".txt": "text/plain",
        ".mp4": "video/mp4",
    }

    media_type = preview_types.get(extension)

    if media_type is None:
        raise HTTPException(
            status_code=415,
            detail=(
                "Inline preview is not supported for this file type. "
                "Convert Word or PowerPoint files to PDF to read them here."
            ),
        )

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        content_disposition_type="inline",
        headers={"X-Content-Type-Options": "nosniff"},
    )


# ============================================================
# DOWNLOAD ORIGINAL FILE WHEN EXPLICITLY REQUESTED
# ============================================================

@app.get("/content/{content_id}/file")
def download_educational_content(
    content_id: int,
    db: Session = Depends(get_db),
):
    item = (
        db.query(ContentItem)
        .filter(ContentItem.id == content_id)
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Educational content not found",
        )

    file_path = UPLOAD_DIR / item.stored_filename

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="The uploaded file could not be found",
        )

    return FileResponse(
        path=str(file_path),
        filename=item.original_filename,
        content_disposition_type="attachment",
    )





# ============================================================
# EDUCATIONAL CONTENT LIKES AND COMMENTS
# ============================================================

def get_content_or_404(db: Session, content_id: int):
    item = (
        db.query(ContentItem)
        .filter(ContentItem.id == content_id)
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Educational content not found",
        )

    return item


def format_content_comment(db: Session, comment: ContentComment):
    comment_user = (
        db.query(User)
        .filter(User.id == comment.user_id)
        .first()
    )

    return {
        "id": comment.id,
        "content_id": comment.content_id,
        "user_id": comment.user_id,
        "username": comment_user.username if comment_user else "Unknown user",
        "content": comment.content,
        "created_at": comment.created_at,
    }


# GET LIKE COUNT AND CURRENT USER'S LIKE STATUS
@app.get("/content/{content_id}/likes")
def get_content_likes(
    content_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_content_or_404(db, content_id)

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    count = (
        db.query(ContentLike)
        .filter(ContentLike.content_id == content_id)
        .count()
    )

    liked = (
        db.query(ContentLike)
        .filter(
            ContentLike.content_id == content_id,
            ContentLike.user_id == user_id,
        )
        .first()
        is not None
    )

    return {
        "content_id": content_id,
        "likes_count": count,
        "liked": liked,
    }


# LIKE EDUCATIONAL CONTENT
@app.post("/content/{content_id}/like", status_code=201)
def like_educational_content(
    content_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_content_or_404(db, content_id)

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(ContentLike)
        .filter(
            ContentLike.content_id == content_id,
            ContentLike.user_id == user_id,
        )
        .first()
    )

    if existing is None:
        db.add(ContentLike(content_id=content_id, user_id=user_id))
        db.commit()

    return {"message": "Content liked", "liked": True}


# UNLIKE EDUCATIONAL CONTENT
@app.delete("/content/{content_id}/like")
def unlike_educational_content(
    content_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_content_or_404(db, content_id)

    like = (
        db.query(ContentLike)
        .filter(
            ContentLike.content_id == content_id,
            ContentLike.user_id == user_id,
        )
        .first()
    )

    if like is not None:
        db.delete(like)
        db.commit()

    return {"message": "Content unliked", "liked": False}


# GET COMMENTS FOR EDUCATIONAL CONTENT
@app.get("/content/{content_id}/comments")
def get_content_comments(
    content_id: int,
    db: Session = Depends(get_db),
):
    get_content_or_404(db, content_id)

    comments = (
        db.query(ContentComment)
        .filter(ContentComment.content_id == content_id)
        .order_by(ContentComment.created_at.asc())
        .all()
    )

    return [
        format_content_comment(db, comment)
        for comment in comments
    ]


# ADD A COMMENT TO EDUCATIONAL CONTENT
@app.post("/content/{content_id}/comments", status_code=201)
def create_content_comment(
    content_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
):
    get_content_or_404(db, content_id)

    user = db.query(User).filter(User.id == data.user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    text = data.content.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Comment cannot be empty",
        )

    comment = ContentComment(
        content_id=content_id,
        user_id=data.user_id,
        content=text,
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return format_content_comment(db, comment)




















# ============================================================
# LIST EDUCATIONAL CONTENT
# ============================================================
@app.get("/content")
def get_educational_content(
    category: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(ContentItem, User)
        .join(User, ContentItem.user_id == User.id)
    )

    if category:
        if category not in CONTENT_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail="Invalid category",
            )

        query = query.filter(ContentItem.category == category)

    results = query.order_by(
        ContentItem.created_at.desc()
    ).all()

    return [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "original_filename": item.original_filename,
            "user_id": item.user_id,
            "created_at": item.created_at,
            "uploader_username": uploader.username,
            "uploader_profile_pic": uploader.profile_pic,
        }
        for item, uploader in results
    ]

# ============================================================
# OPEN / DOWNLOAD EDUCATIONAL CONTENT
# ============================================================

@app.get("/content/{content_id}/file")
def open_educational_content(
    content_id: int,
    db: Session = Depends(get_db),
):
    item = (
        db.query(ContentItem)
        .filter(ContentItem.id == content_id)
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Educational content not found",
        )

    file_path = UPLOAD_DIR / item.stored_filename

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="The uploaded file could not be found",
        )

    return FileResponse(
        path=str(file_path),
        filename=item.original_filename,
    )






# ============================================================
# USER ENDPOINTS
# ============================================================

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.username == user.username) |
        (User.email == user.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists",
        )

    return create_user_db(db, user)


@app.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    return get_users_db(db)


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user_db(db, user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
):
    existing_user = db.query(User).filter(
        (
            (User.username == user.username) |
            (User.email == user.email)
        ) &
        (User.id != user_id)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists",
        )

    updated_user = update_user_db(db, user_id, user)

    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return updated_user


@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    deleted_user = delete_user_db(db, user_id)

    if deleted_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted successfully"}


# ============================================================
# POST HELPERS
# ============================================================

def get_post_or_404(db: Session, post_id: int):
    post = db.query(Post).filter(Post.id == post_id).first()

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    return post


def format_post(db: Session, post: Post):
    author = db.query(User).filter(User.id == post.author_id).first()

    return {
        "id": post.id,
        "author_id": post.author_id,
        "author_username": author.username if author else "Unknown user",
        "content": post.content,
        "created_at": post.created_at,
        "likes_count": db.query(Like).filter(
            Like.post_id == post.id
        ).count(),
        "comments_count": db.query(Comment).filter(
            Comment.post_id == post.id
        ).count(),
    }


def format_comment(db: Session, comment: Comment):
    user = db.query(User).filter(User.id == comment.user_id).first()

    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "username": user.username if user else "Unknown user",
        "post_id": comment.post_id,
        "content": comment.content,
        "created_at": comment.created_at,
    }


# ============================================================
# CREATE A POST
# ============================================================

@app.post("/posts", response_model=PostResponse, status_code=201)
def create_post(data: PostCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.author_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Post cannot be empty")

    post = Post(
        author_id=data.author_id,
        content=data.content.strip(),
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return format_post(db, post)


# ============================================================
# VIEW POSTS
# ============================================================

@app.get("/posts", response_model=List[PostResponse])
def get_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    return [format_post(db, post) for post in posts]


@app.get("/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = get_post_or_404(db, post_id)
    return format_post(db, post)


@app.get("/users/{user_id}/posts", response_model=List[PostResponse])
def get_user_posts(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    posts = (
        db.query(Post)
        .filter(Post.author_id == user_id)
        .order_by(Post.created_at.desc())
        .all()
    )

    return [format_post(db, post) for post in posts]


# ============================================================
# UPDATE AND DELETE POSTS
# ============================================================

@app.put("/posts/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    data: PostUpdate,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    post = get_post_or_404(db, post_id)

    if post.author_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only edit your own posts",
        )

    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Post cannot be empty")

    post.content = data.content.strip()
    db.commit()
    db.refresh(post)

    return format_post(db, post)


@app.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    post = get_post_or_404(db, post_id)

    if post.author_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own posts",
        )

    db.delete(post)
    db.commit()

    return {"message": "Post deleted successfully"}


# ============================================================
# LIKE AND UNLIKE POSTS
# ============================================================

@app.post("/posts/{post_id}/like", status_code=201)
def like_post(
    post_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_post_or_404(db, post_id)

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing_like = db.query(Like).filter(
        Like.user_id == user_id,
        Like.post_id == post_id,
    ).first()

    if existing_like:
        raise HTTPException(
            status_code=400,
            detail="You have already liked this post",
        )

    like = Like(user_id=user_id, post_id=post_id)
    db.add(like)
    db.commit()

    return {"message": "Post liked successfully"}


@app.delete("/posts/{post_id}/like")
def unlike_post(
    post_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    get_post_or_404(db, post_id)

    like = db.query(Like).filter(
        Like.user_id == user_id,
        Like.post_id == post_id,
    ).first()

    if like is None:
        raise HTTPException(status_code=404, detail="Like not found")

    db.delete(like)
    db.commit()

    return {"message": "Post unliked successfully"}


# ============================================================
# CREATE AND VIEW COMMENTS
# ============================================================

@app.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=201,
)
def create_comment(
    post_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
):
    get_post_or_404(db, post_id)

    user = db.query(User).filter(User.id == data.user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not data.content.strip():
        raise HTTPException(
            status_code=400,
            detail="Comment cannot be empty",
        )

    comment = Comment(
        user_id=data.user_id,
        post_id=post_id,
        content=data.content.strip(),
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    # Return the newly created comment, matching CommentResponse.
    return format_comment(db, comment)


@app.get(
    "/posts/{post_id}/comments",
    response_model=List[CommentResponse],
)
def get_comments(post_id: int, db: Session = Depends(get_db)):
    get_post_or_404(db, post_id)

    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

    return [format_comment(db, comment) for comment in comments]


# ============================================================
# DELETE YOUR OWN COMMENT
# ============================================================

@app.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    comment = db.query(Comment).filter(
        Comment.id == comment_id
    ).first()

    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own comments",
        )

    db.delete(comment)
    db.commit()

    return {"message": "Comment deleted successfully"}

# ============================================================
# ADMIN DASHBOARD PAGE
# ============================================================

@app.get("/admin", include_in_schema=False)
def admin_dashboard():
    admin_file = Path(__file__).resolve().parent / "admin.html"

    if not admin_file.is_file():
        raise HTTPException(
            status_code=404,
            detail="Admin page not found",
        )

    return FileResponse(
        path=str(admin_file),
        media_type="text/html",
    )


# ============================================================
# ADMIN: DELETE SELECTED EDUCATIONAL CONTENT
# ============================================================


class ContentBulkDelete(BaseModel):
    content_ids: List[int]



@app.delete("/admin/content")
def delete_selected_content(
    data: ContentBulkDelete,
    db: Session = Depends(get_db),
):
    content_ids = list(set(data.content_ids))

    if not content_ids:
        raise HTTPException(
            status_code=400,
            detail="Select at least one content item",
        )

    # Find all requested content records.
    items = (
        db.query(ContentItem)
        .filter(ContentItem.id.in_(content_ids))
        .all()
    )

    found_ids = {item.id for item in items}
    missing_ids = set(content_ids) - found_ids

    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Content not found for IDs: {sorted(missing_ids)}",
        )

    # Save the server-generated file paths before deleting records.
    file_paths = [
        UPLOAD_DIR / item.stored_filename
        for item in items
    ]

    try:
        # Delete records. Database cascades remove associated likes
        # and comments because SQLite foreign keys are enabled.
        for item in items:
            db.delete(item)

        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not delete selected content",
        )

    # Remove physical files after the database commit succeeds.
    failed_file_deletions = []

    for path in file_paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            failed_file_deletions.append(path.name)

    return {
        "message": "Selected content deleted",
        "deleted_ids": sorted(found_ids),
        "deleted_count": len(found_ids),
        "failed_file_deletions": failed_file_deletions,
    }  




# ============================================================
# ADMIN: DASHBOARD STATISTICS
# ============================================================

@app.get("/admin/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    total_content = db.query(ContentItem).count()

    return {
        "total_users": total_users,
        "total_content": total_content,
    }
