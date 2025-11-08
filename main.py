from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import inspect, create_engine, text
import models
from database import SessionLocal, engine, DATABASE_URL
import time
from datetime import datetime

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

@app.get("/", response_class=HTMLResponse)
def read_tasks(request: Request, db: Session = Depends(get_db)):
    pending_tasks = db.query(models.Task).filter(models.Task.completed == False).all()
    completed_tasks = db.query(models.Task).filter(models.Task.completed == True).all()
    return templates.TemplateResponse("index.html", {"request": request, "pending_tasks": pending_tasks, "completed_tasks": completed_tasks})

@app.post("/add", response_class=RedirectResponse)
def add_task(title: str = Form(...), description: str = Form(None), deadline: str = Form(None), db: Session = Depends(get_db)):
    deadline_obj = datetime.strptime(deadline, "%Y-%m-%d").date() if deadline else None
    new_task = models.Task(title=title, description=description, deadline=deadline_obj)
    db.add(new_task)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/complete/{task_id}", response_class=RedirectResponse)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        task.completed = True
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/delete/{task_id}", response_class=RedirectResponse)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
    return RedirectResponse(url="/", status_code=303)
