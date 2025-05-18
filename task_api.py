from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import uvicorn

# Define Task data model
class TaskBase(BaseModel):
    name: str
    status: str
    due_date: date
    capacite_c: int
    effort_c: int

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    
    class Config:
        orm_mode = True

# Initialize FastAPI app
app = FastAPI(title="Task Management API", 
              description="API for managing Task objects",
              version="1.0.0")

# In-memory database (replace with actual database in production)
tasks_db = []
task_id_counter = 1

# API routes
@app.post("/tasks/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate):
    """Create a new task"""
    global task_id_counter
    new_task = Task(
        id=task_id_counter,
        name=task.name,
        status=task.status,
        due_date=task.due_date,
        capacite_c=task.capacite_c,
        effort_c=task.effort_c
    )
    tasks_db.append(new_task)
    task_id_counter += 1
    return new_task

@app.get("/tasks/", response_model=List[Task])
def read_tasks(skip: int = 0, limit: int = 100):
    """Retrieve a list of tasks"""
    return tasks_db[skip : skip + limit]

@app.get("/tasks/{task_id}", response_model=Task)
def read_task(task_id: int):
    """Retrieve a specific task by ID"""
    for task in tasks_db:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task_update: TaskBase):
    """Update an existing task"""
    for i, task in enumerate(tasks_db):
        if task.id == task_id:
            updated_task = Task(
                id=task_id,
                name=task_update.name,
                status=task_update.status,
                due_date=task_update.due_date,
                capacite_c=task_update.capacite_c,
                effort_c=task_update.effort_c
            )
            tasks_db[i] = updated_task
            return updated_task
    raise HTTPException(status_code=404, detail="Task not found")

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    """Delete a task"""
    for i, task in enumerate(tasks_db):
        if task.id == task_id:
            tasks_db.pop(i)
            return
    raise HTTPException(status_code=404, detail="Task not found")

# Run the server
if __name__ == "__main__":
    uvicorn.run("task_api:app", host="0.0.0.0", port=8000, reload=True)