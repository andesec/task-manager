from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine
import time

# Retry mechanism for database connection
for i in range(10):
    try:
        models.Base.metadata.create_all(bind=engine)
        print("Database tables created.")
        break
    except Exception as e:
        print(f"Database connection failed. Retrying... ({i+1}/10)")
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
def add_task(title: str = Form(...), db: Session = Depends(get_db)):
    new_task = models.Task(title=title)
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
