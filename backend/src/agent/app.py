# mypy: disable - error - code = "no-untyped-def,misc"
import pathlib
from fastapi import FastAPI, Response, Request, File, UploadFile, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .agent import evaluation_agent, rating_agent
from .tools import analyze_resume_file
import json
import asyncio
from contextlib import asynccontextmanager
from pydantic import BaseModel
from datetime import timedelta

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from typing import Dict, Any
import uuid

# Import authentication modules
from .database import get_db, create_tables
from .auth import create_access_token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES
from .user_service import UserService
from .schemas import UserCreate, LoginRequest, TokenResponse, UserResponse, MessageResponse
from .models import User
from sqlalchemy.ext.asyncio import AsyncSession

# --- ADK Setup ---
# This follows the modern programmatic pattern for running an ADK agent.
APP_NAME = "resume-optimizer-app"
USER_ID = "default_user"
SESSION_ID = "default_session"

# 1. Set up session management
session_service = InMemorySessionService()

# 2. Create separate runners for both agents
evaluation_runner = Runner(agent=evaluation_agent, app_name=APP_NAME, session_service=session_service)
rating_runner = Runner(agent=rating_agent, app_name=APP_NAME, session_service=session_service)

# Store resume analysis results temporarily
resume_analyses: Dict[str, Dict[str, Any]] = {}
# --- End ADK Setup ---

# Pydantic models for request/response
class ResumeEvaluationRequest(BaseModel):
    resume_text: str
    job_description: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup
    await create_tables()
    
    # Create the default session on startup
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    yield
    # No cleanup needed for in-memory session service


# Define the FastAPI app
app = FastAPI(lifespan=lifespan, title="Resume Optimizer API", description="AI-powered resume optimization using Gemini")


# Add CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for production deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (built React frontend) - will be added at the end after all routes

# === AUTHENTICATION ENDPOINTS ===

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    try:
        user = await UserService.create_user(db, user_create)
        await db.commit()
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )


@app.post("/auth/login", response_model=TokenResponse)
async def login(login_request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return access token."""
    user = await UserService.authenticate_user(db, login_request.email, login_request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is deactivated"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        user=user
    )


@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current authenticated user information."""
    return current_user


@app.get("/auth/protected", response_model=MessageResponse)
async def protected_route(current_user: User = Depends(get_current_active_user)):
    """Example protected route that requires authentication."""
    return MessageResponse(
        message=f"Hello {current_user.username}! You are authenticated.",
        success=True
    )

# === RESUME ANALYSIS ENDPOINTS ===

@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload and analyze a resume file (PDF, DOC, TXT).
    Returns analysis results and a unique analysis ID.
    """
    try:
        # Validate file type
        allowed_types = ["application/pdf", "application/msword", 
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "text/plain"]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file.content_type}. Supported types: PDF, DOC, DOCX, TXT"
            )
        
        # Read file content
        content = await file.read()
        
        # Determine file extension
        file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else 'pdf'
        
        # Analyze the resume
        analysis_result = analyze_resume_file(content, file_extension)
        
        if not analysis_result.get("success"):
            raise HTTPException(status_code=500, detail=analysis_result.get("error", "Resume analysis failed"))
        
        # Store analysis with unique ID
        analysis_id = str(uuid.uuid4())
        resume_analyses[analysis_id] = {
            "analysis": analysis_result,
            "filename": file.filename,
            "file_size": len(content),
            "file_type": file.content_type
        }
        
        return {
            "success": True,
            "analysis_id": analysis_id,
            "filename": file.filename,
            "file_size": len(content),
            "analysis": analysis_result.get("analysis", ""),
            "message": "Resume uploaded and analyzed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume upload failed: {str(e)}")



@app.post("/evaluate-resume")
async def evaluate_resume_directly(request: ResumeEvaluationRequest):
    """
    Evaluate, rate, and generate an improved resume using sequential agents.
    Step 1: Evaluation agent analyzes the resume
    Step 2: Rating agent provides scores and generates improved version
    """
    try:
        if not request.resume_text.strip():
            raise HTTPException(status_code=400, detail="Resume text cannot be empty")
        
        if not request.job_description.strip():
            raise HTTPException(status_code=400, detail="Job description cannot be empty")
        
        # Get skills analysis first
        from .tools import analyze_skills_matching
        skills_analysis = analyze_skills_matching(request.resume_text, request.job_description)
        
        # Step 1: Evaluation Agent - Just provide the data
        evaluation_prompt = f"""
        RESUME:
        {request.resume_text}

        JOB DESCRIPTION:
        {request.job_description}

        SKILLS ANALYSIS DATA:
        {skills_analysis}
        """
        
        evaluation_content = types.Content(
            role="user", parts=[types.Part(text=evaluation_prompt)]
        )
        
        evaluation_report = ""
        chunk_count = 0
        async for event in evaluation_runner.run_async(
            user_id=USER_ID, session_id=SESSION_ID, new_message=evaluation_content
        ):
            if event.content and event.content.parts:
                chunk_count += 1
                chunk_text = event.content.parts[0].text
                evaluation_report += chunk_text
                print(f"DEBUG: Evaluation chunk {chunk_count}: {len(chunk_text)} chars")
        
        print(f"DEBUG: Total evaluation report: {len(evaluation_report)} characters")
        
        # Parse JSON response from structured output
        try:
            evaluation_data = json.loads(evaluation_report)
            print("DEBUG: Successfully parsed evaluation JSON")
        except json.JSONDecodeError as e:
            print(f"DEBUG: Failed to parse evaluation JSON: {e}")
            # Fallback to original text format
            evaluation_data = {"raw_text": evaluation_report}
        
        # Step 2: Rating Agent - Use evaluation report as primary source
        rating_prompt = f"""
        TASK: Base your ratings and improvements on the evaluation report from the first agent.

        EVALUATION REPORT FROM FIRST AGENT (PRIMARY SOURCE):
        {evaluation_report}

        SUPPORTING DATA:
        SKILLS ANALYSIS: {skills_analysis}
        ORIGINAL RESUME: {request.resume_text}
        JOB DESCRIPTION: {request.job_description}

        INSTRUCTIONS:
        - Use the evaluation report findings as your primary source for ratings
        - Reference specific issues and strengths mentioned in the evaluation
        - Create improved resume that addresses the gaps identified in the evaluation
        - Use skills analysis data for quantified insights (match_percentage, missing_skills)
        """
        
        rating_content = types.Content(
            role="user", parts=[types.Part(text=rating_prompt)]
        )
        
        rating_results = ""
        rating_chunk_count = 0
        
        try:
            async for event in rating_runner.run_async(
                user_id=USER_ID, session_id=SESSION_ID, new_message=rating_content
            ):
                if event.content and event.content.parts:
                    rating_chunk_count += 1
                    chunk_text = event.content.parts[0].text
                    rating_results += chunk_text
                    print(f"DEBUG: Rating chunk {rating_chunk_count}: {len(chunk_text)} chars")
                        
        except Exception as e:
            print(f"DEBUG: Rating stream error: {e}")
            
        print(f"DEBUG: Total rating results: {len(rating_results)} characters")
        
        # Parse JSON response from structured output
        try:
            rating_data = json.loads(rating_results)
            print("DEBUG: Successfully parsed rating JSON")
        except json.JSONDecodeError as e:
            print(f"DEBUG: Failed to parse rating JSON: {e}")
            # Fallback to original text format
            rating_data = {"raw_text": rating_results}
        
        return {
            "success": True,
            "structured_evaluation": evaluation_data,
            "structured_rating": rating_data,
            "workflow_type": "sequential_evaluation_and_rating",
            "message": "Resume evaluation and rating completed using sequential agents"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume evaluation failed: {str(e)}")

# === FRONTEND STATIC FILES ===
# Mount React frontend after all API routes (must be last)

import os
from pathlib import Path

frontend_dist_path = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"

if frontend_dist_path.exists() and (frontend_dist_path / "index.html").exists():
    # Mount static files at root - this catches all non-API routes
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="static")
    print(f"✅ Frontend mounted from: {frontend_dist_path}")
else:
    print(f"⚠️ Frontend build not found at: {frontend_dist_path}")
    
    @app.get("/")
    async def root():
        return {"message": "Resume Analyzer API", "status": "Backend running", "note": "Frontend build not found"}