from fastapi import FastAPI, HTTPException, Depends, status, Security, Request, Response, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, ValidationError
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import uvicorn
from enum import Enum
import os
import requests
from jose import JWTError, jwt
import json
from urllib.parse import urlencode

# Try to import dotenv, but continue if it's not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, just continue
    pass

# Security configuration
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Salesforce OAuth configuration
CLIENT_ID = os.getenv("SALESFORCE_CLIENT_ID", "3MVG9IXUyidRC0l2tzIXfjoVPzLqAsHzSwWPUL9ik5229A3AKolaFLRE8nZxnELmJCK0sedUCEKPqvd.LpQtW")
CLIENT_SECRET = os.getenv("SALESFORCE_CLIENT_SECRET", "0387FDCB815A02A5496DD87176671C78FE0DB29C2A6CC3CD5C604678E34517D7")
REDIRECT_URI = os.getenv("SALESFORCE_REDIRECT_URI", "http://localhost:8000/oauth/callback")
AUTH_URL = os.getenv("SALESFORCE_AUTH_URL", "https://login.salesforce.com/services/oauth2/authorize")
TOKEN_URL = os.getenv("SALESFORCE_TOKEN_URL", "https://login.salesforce.com/services/oauth2/token")

# Storage for tokens
tokens_db = {}  # {user_id: {"access_token": token, "refresh_token": token, "scopes": []}}

# Define enums for constrained fields
class StatusEnum(str, Enum):
    PAS_COMMENCE = "Pas commencé"
    EN_COURS = "En cours"
    TERMINEE = "Terminée"

class PriorityEnum(str, Enum):
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"

# User models
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    instance_url: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    scopes: List[str] = []

class UserInDB(User):
    password: str

# Task models
class TaskBase(BaseModel):
    Task_Name__c: str
    Status: StatusEnum
    Capacite__c: int
    Effort_Realise__c: int
    subject: str = "Other"  # Default value
    Priority: PriorityEnum

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    
    class Config:
        orm_mode = True

# Initialize FastAPI app
app = FastAPI(title="Task Management API", 
              description="API for managing Task objects with Salesforce OAuth 2.0 authentication",
              version="1.0.0")

# Define a custom OAuth2 scheme that will validate tokens
class OAuth2SalesforceBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        token = await super().__call__(request)
        return token

oauth2_scheme = OAuth2SalesforceBearer(
    tokenUrl="token",
    scopes={
        "api": "Access to API",
        "refresh_token": "Get refresh token"
    }
)

# In-memory database with 20 pre-populated tasks
tasks_db = []

# Task names to use for pre-populated tasks
task_names = [
    "api test 9",
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
    "Implement logging and monitoring",
    "Prepare release notes for v1.0"
]

# Create and populate tasks
for i in range(1, 21):
    status_value = StatusEnum.EN_COURS if i % 3 == 1 else (StatusEnum.TERMINEE if i % 3 == 2 else StatusEnum.PAS_COMMENCE)
    priority_value = PriorityEnum.HIGH if i % 3 == 0 else (PriorityEnum.NORMAL if i % 3 == 1 else PriorityEnum.LOW)
    
    tasks_db.append(
        Task(
            id=i,
            Task_Name__c=task_names[i-1] if i-1 < len(task_names) else f"Task {i}",
            Status=status_value,
            Capacite__c=80 - (i % 5) * 10,
            Effort_Realise__c=20 + (i % 4) * 15,
            Priority=priority_value
        )
    )

# Authentication functions
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Here we would normally validate the token with Salesforce
    # For simplicity, we'll just check if it exists in our tokens_db
    for user_id, token_data in tokens_db.items():
        if token_data.get("access_token") == token:
            # Create a simple user object
            user = User(
                username=user_id,
                email=f"{user_id}@example.com",
                full_name=f"User {user_id}",
                disabled=False,
                scopes=["api"]
            )
            return user
    
    raise credentials_exception

# Salesforce OAuth endpoints
@app.get("/oauth/authorize")
async def authorize():
    """Redirect to Salesforce authorization page"""
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "api refresh_token"
    }
    
    authorize_url = f"{AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=authorize_url)

@app.get("/oauth/callback")
async def oauth_callback(code: str = Query(...), state: Optional[str] = Query(None)):
    """Handle the callback from Salesforce"""
    # Exchange authorization code for tokens
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI
    }
    
    response = requests.post(TOKEN_URL, data=token_data)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to obtain access token: {response.text}"
        )
    
    tokens = response.json()
    
    # Store tokens (in a real app, associate with the current user)
    user_id = "user_" + tokens["access_token"][-8:]  # Use last 8 chars of token as user ID
    tokens_db[user_id] = tokens
    
    return JSONResponse(content={
        "message": "Successfully authenticated with Salesforce",
        "user_id": user_id,
        "token_type": tokens["token_type"],
        "access_token": tokens["access_token"][:10] + "...",  # Show only the beginning
        "instance_url": tokens.get("instance_url", "N/A")
    })

@app.post("/oauth/token")
async def token(code: Optional[str] = None, refresh_token: Optional[str] = None, grant_type: str = "authorization_code"):
    """Exchange authorization code or refresh token for access token"""
    if grant_type == "authorization_code" and code:
        # Exchange authorization code for tokens
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI
        }
    elif grant_type == "refresh_token" and refresh_token:
        # Exchange refresh token for new access token
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request parameters"
        )
    
    response = requests.post(TOKEN_URL, data=token_data)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to obtain access token: {response.text}"
        )
    
    tokens = response.json()
    
    # Store tokens (in a real app, associate with the current user)
    user_id = "user_" + tokens["access_token"][-8:]
    tokens_db[user_id] = tokens
    
    return Token(
        access_token=tokens["access_token"],
        token_type=tokens["token_type"],
        expires_in=tokens.get("expires_in", 7200),
        refresh_token=tokens.get("refresh_token"),
        scope=tokens.get("scope"),
        instance_url=tokens.get("instance_url")
    )

@app.get("/users/me/")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# API routes with authentication
@app.post("/tasks/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, current_user: User = Depends(get_current_user)):
    """Create a new task"""
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
def read_tasks(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user)):
    """Retrieve a list of tasks"""
    return tasks_db[skip : skip + limit]

@app.get("/tasks/{task_id}", response_model=Task)
def read_task(task_id: int, current_user: User = Depends(get_current_user)):
    """Retrieve a specific task by ID"""
    for task in tasks_db:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task_update: TaskBase, current_user: User = Depends(get_current_user)):
    """Update an existing task"""
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
def delete_task(task_id: int, current_user: User = Depends(get_current_user)):
    """Delete a task"""
    for i, task in enumerate(tasks_db):
        if task.id == task_id:
            tasks_db.pop(i)
            return
    raise HTTPException(status_code=404, detail="Task not found")

# Public status endpoint (no authentication required)
@app.get("/status")
def get_status():
    """Check API status (public endpoint)"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "salesforce_oauth": {
            "configured": all([
                CLIENT_ID != "default_client_id",
                CLIENT_SECRET != "default_client_secret"
            ]),
            "auth_url": AUTH_URL,
            "token_url": TOKEN_URL,
            "redirect_uri": REDIRECT_URI
        }
    }

# Add helpful endpoint to initiate auth flow
@app.get("/login")
def login_redirect():
    """Redirect to the OAuth authorization endpoint"""
    return RedirectResponse(url="/oauth/authorize")

# Run the server
if __name__ == "__main__":
    uvicorn.run("task_api:app", host="0.0.0.0", port=8000, reload=True)
