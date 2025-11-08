from sqlalchemy import Boolean, Column, Integer, String, Date
from database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    deadline = Column(Date, nullable=True)
    completed = Column(Boolean, default=False)
