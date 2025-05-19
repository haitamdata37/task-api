from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
import requests

# Salesforce OAuth credentials (Hardcoded — for testing only)
CLIENT_ID = "3MVG9IXUyidRC0l2tzIXfjoVPzLqAsHzSwWPUL9ik5229A3AKolaFLRE8nZxnELmJCK0sedUCEKPqvd.LpQtW"
CLIENT_SECRET = "0387FDCB815A02A5496DD87176671C78FE0DB29C2A6CC3CD5C604678E34517D7"
REDIRECT_URI = "http://localhost:8000/oauth/callback"
AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"

# Enums
class StatusEnum(str, Enum):
    PAS_COMMENCE = "Pas commencé"
    EN_COURS = "En cours"
    TERMINEE = "Terminée"

class PriorityEnum(str, Enum):
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"

# Pydantic models
class TaskBase(BaseModel):
    Task_Name__c: str
    Status: StatusEnum
    Capacite__c: int
    Effort_Realise__c: int
    subject: str = "Other"
    Priority: PriorityEnum

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    class Config:
        orm_mode = True

# FastAPI app
app = FastAPI(title="Task Management API with Salesforce OAuth2.0")

# In-memory task list
tasks_db = [
    Task(
        id=i,
        Task_Name__c="Placeholder",
        Status=StatusEnum.EN_COURS if i % 3 == 1 else 
              (StatusEnum.TERMINEE if i % 3 == 2 else StatusEnum.PAS_COMMENCE),
        Capacite__c=80 - (i % 5) * 10,
        Effort_Realise__c=20 + (i % 4) * 15,
        subject="Other",
        Priority=PriorityEnum.HIGH if i % 3 == 0 else 
                (PriorityEnum.NORMAL if i % 3 == 1 else PriorityEnum.LOW)
    )
    for i in range(1, 21)
]

task_names = [
    "api test 6",
    "Complete project requirements documentation",
    "Develop frontend UI components",
    "Set up database schema and models",
    "Implement API authentication",
    "Create automated test suite",
    "Perform security audit",
    "Optimize database queries",
    "Deploy application to staging",
    "Conduct user acceptance testing",
    "Fix reported bugs in module A",
    "Update user documentation",
    "Refactor legacy code module",
    "Integrate with third-party payment API",
    "Create admin dashboard",
    "Implement user notification system",
    "Perform load testing",
    "Migrate data from old system",
    "Review and improve error handling",
    "Implement logging and monitoring"
]

for i, task in enumerate(tasks_db):
    task.Task_Name__c = task_names[i]

# CRUD routes
@app.post("/tasks/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate):
    new_task = Task(
        id=len(tasks_db) + 1,
        Task_Name__c=task.Task_Name__c,
        Status=task.Status,
        Capacite__c=task.Capacite__c,
        Effort_Realise__c=task.Effort_Realise__c,
        subject=task.subject,
        Priority=task.Priority
    )
    tasks_db.append(new_task)
    return new_task

@app.get("/tasks/", response_model=List[Task])
def read_tasks(skip: int = 0, limit: int = 100):
    return tasks_db[skip: skip + limit]

@app.get("/tasks/{task_id}", response_model=Task)
def read_task(task_id: int):
    for task in tasks_db:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task_update: TaskBase):
    for i, task in enumerate(tasks_db):
        if task.id == task_id:
            updated_task = Task(
                id=task_id,
                Task_Name__c=task_update.Task_Name__c,
                Status=task_update.Status,
                Capacite__c=task_update.Capacite__c,
                Effort_Realise__c=task_update.Effort_Realise__c,
                subject=task_update.subject,
                Priority=task_update.Priority
            )
            tasks_db[i] = updated_task
            return updated_task
    raise HTTPException(status_code=404, detail="Task not found")

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    for i, task in enumerate(tasks_db):
        if task.id == task_id:
            tasks_db.pop(i)
            return
    raise HTTPException(status_code=404, detail="Task not found")

# --- Salesforce OAuth2 Routes ---
@app.get("/login/salesforce")
def login_salesforce():
    url = (
        f"{AUTH_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return RedirectResponse(url=url)

@app.get("/oauth/callback")
def oauth_callback(code: Optional[str] = None):
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    response = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    })

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to get access token")

    token_data = response.json()
    return token_data  # Or store/use token as needed

# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("task_api:app", host="0.0.0.0", port=8000, reload=True)
