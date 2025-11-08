from fastapi import FastAPI, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import inspect, create_engine, text
import models
from database import SessionLocal, engine, DATABASE_URL
import time
from datetime import datetime
from auth import Hasher
import os

# Retry mechanism for database connection and schema migration
for i in range(10):
    try:
        # Check for existing tables and columns
        db_engine = create_engine(DATABASE_URL)
        inspector = inspect(db_engine)
        
        # Create tables if they don't exist
        models.Base.metadata.create_all(bind=db_engine)
        print("Database tables created or already exist.")

        # Check for columns in the tasks table
        columns = [col['name'] for col in inspector.get_columns('tasks')]
        with db_engine.connect() as connection:
            if 'description' not in columns:
                connection.execute(text("ALTER TABLE tasks ADD COLUMN description VARCHAR"))
                connection.commit()
                print("Added 'description' column to 'tasks' table.")
            if 'deadline' not in columns:
                connection.execute(text("ALTER TABLE tasks ADD COLUMN deadline DATE"))
                connection.commit()
                print("Added 'deadline' column to 'tasks' table.")
            if 'user_id' not in columns:
                connection.execute(text("ALTER TABLE tasks ADD COLUMN user_id INTEGER"))
                connection.commit()
                print("Added 'user_id' column to 'tasks' table.")
        
        break
    except Exception as e:
        print(f"Database connection or migration failed. Retrying... ({i+1}/10)")
        print(e)
        time.sleep(2)


app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://app.task-manager.orb.local",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not found in environment variables")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": f"An unexpected error occurred: {exc}"},
    )

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return user

@app.post("/register", response_class=RedirectResponse)
def register_user(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    
    hashed_password = Hasher.get_password_hash(password)
    new_user = models.User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/login", response_class=RedirectResponse)
def login_user(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not Hasher.verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout", response_class=RedirectResponse)
def logout_user(request: Request):
    request.session.pop("user_id", None)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/", response_class=HTMLResponse)
def read_tasks(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user:
        return templates.TemplateResponse("login.html", {"request": request}) # Will create login.html later
    
    pending_tasks = db.query(models.Task).filter(models.Task.completed == False, models.Task.user_id == current_user.id).all()
    completed_tasks = db.query(models.Task).filter(models.Task.completed == True, models.Task.user_id == current_user.id).all()
    return templates.TemplateResponse("index.html", {"request": request, "pending_tasks": pending_tasks, "completed_tasks": completed_tasks, "current_user": current_user})

@app.post("/add", response_class=RedirectResponse)
def add_task(title: str = Form(...), description: str = Form(None), deadline: str = Form(None), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    deadline_obj = datetime.strptime(deadline, "%Y-%m-%d").date() if deadline else None
    new_task = models.Task(title=title, description=description, deadline=deadline_obj, user_id=current_user.id)
    db.add(new_task)
    db.commit()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/complete/{task_id}", response_class=RedirectResponse)
def complete_task(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.user_id == current_user.id).first()
    if task:
        task.completed = True
        db.commit()
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not owned by user")
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/delete/{task_id}", response_class=RedirectResponse)
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.user_id == current_user.id).first()
    if task:
        db.delete(task)
        db.commit()
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not owned by user")
    return RedirectResponse(url="/", status_code=303)
