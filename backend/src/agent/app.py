# mypy: disable - error - code = "no-untyped-def,misc"
import pathlib
from fastapi import FastAPI, Response, Request, File, UploadFile, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .agent import evaluation_agent, rating_agent, experience_optimizer_agent
from .tools import analyze_resume_file
import json
import asyncio
from contextlib import asynccontextmanager
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from typing import Dict, Any
import uuid

# --- ADK Setup ---
# This follows the modern programmatic pattern for running an ADK agent.
APP_NAME = "resume-optimizer-app"
USER_ID = "default_user"
SESSION_ID = "default_session"

# 1. Set up session management
session_service = InMemorySessionService()

# 2. Create separate runners for all agents
evaluation_runner = Runner(agent=evaluation_agent, app_name=APP_NAME, session_service=session_service)
rating_runner = Runner(agent=rating_agent, app_name=APP_NAME, session_service=session_service)
optimizer_runner = Runner(agent=experience_optimizer_agent, app_name=APP_NAME, session_service=session_service)

# Store resume analysis results temporarily
resume_analyses: Dict[str, Dict[str, Any]] = {}
# --- End ADK Setup ---

# Pydantic models for request/response
class ResumeEvaluationRequest(BaseModel):
    resume_text: str
    job_description: str

class ExperienceItem(BaseModel):
    title: str
    company: str
    duration: str
    description: str
    skills: list[str] = []

class SmartResumeRequest(BaseModel):
    resume_text: str
    job_description: str
    pool_experiences: list[ExperienceItem] = []  # Optional pool of additional experiences

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all required in-memory sessions on startup
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    # Session for optimizer agent
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=USER_ID + "_optimizer"
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
            "extracted_text": analysis_result.get("extracted_text", ""),  # The actual resume text
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
        JOB DESCRIPTION: {request.job_description}

        ==================== ORIGINAL RESUME TEXT (FOR EXACT TEXT EXTRACTION) ====================
        IMPORTANT: When creating paraphrasing suggestions, you MUST copy text from this resume EXACTLY.
        Do NOT paraphrase, improve, or modify the current_text - copy it character-by-character.

        {request.resume_text}

        ==================== END OF RESUME TEXT ====================

        INSTRUCTIONS:
        - Use the evaluation report findings as your primary source for ratings
        - Reference specific issues and strengths mentioned in the evaluation
        - For paraphrasing_suggestion.current_text: Copy text EXACTLY from the resume above
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
            
            # Validate paraphrasing suggestions
            if "priority_recommendations" in rating_data:
                validated_count = 0
                for rec in rating_data["priority_recommendations"]:
                    if "paraphrasing_suggestion" in rec and rec["paraphrasing_suggestion"]:
                        current_text = rec["paraphrasing_suggestion"].get("current_text", "")
                        if current_text and current_text in request.resume_text:
                            validated_count += 1
                        else:
                            print(f"WARNING: Paraphrasing suggestion text not found in resume: {current_text[:100]}...")
                print(f"DEBUG: Validated {validated_count}/{len(rating_data['priority_recommendations'])} paraphrasing suggestions")
                
        except json.JSONDecodeError as e:
            print(f"DEBUG: Failed to parse rating JSON: {e}")
            # Fallback to original text format
            rating_data = {"raw_text": rating_results}
        
        # Ensure skills analysis data is included in evaluation response
        if "matching_skills" not in evaluation_data or not evaluation_data.get("matching_skills"):
            evaluation_data["matching_skills"] = skills_analysis.get("matching_skills", [])
        if "missing_skills" not in evaluation_data or not evaluation_data.get("missing_skills"):
            evaluation_data["missing_skills"] = skills_analysis.get("missing_skills", [])
        if "job_match_percentage" not in evaluation_data or not evaluation_data.get("job_match_percentage"):
            evaluation_data["job_match_percentage"] = skills_analysis.get("match_percentage", 0)
        
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

@app.post("/analyze-experience-swaps")
async def analyze_experience_swaps(request: SmartResumeRequest):
    """
    Step 1: Analyze and recommend experience swaps without applying them.
    Returns recommendations for user review.
    """
    try:
        if not request.resume_text.strip():
            raise HTTPException(status_code=400, detail="Resume text cannot be empty")
        
        if not request.job_description.strip():
            raise HTTPException(status_code=400, detail="Job description cannot be empty")
        
        # If no pool experiences provided, fall back to regular evaluation
        if not request.pool_experiences:
            return await evaluate_resume_directly(ResumeEvaluationRequest(
                resume_text=request.resume_text,
                job_description=request.job_description
            ))
        
        # Step 1: Run optimizer agent to compare and recommend swaps
        optimizer_prompt = f"""
        ORIGINAL RESUME:
        {request.resume_text}

        JOB DESCRIPTION:
        {request.job_description}

        POOL OF ADDITIONAL EXPERIENCES:
        {json.dumps([{
            'title': exp.title,
            'company': exp.company,
            'duration': exp.duration,
            'description': exp.description,
            'skills': exp.skills
        } for exp in request.pool_experiences], indent=2)}

        TASK:
        1. Extract work experiences from the ORIGINAL RESUME
        2. Score each resume experience's relevance to the job (0-100)
        3. For each resume experience, find the best pool experience that could replace it
        4. Score that pool experience's relevance (0-100)
        5. Recommend replacement ONLY if pool experience is 20+ points better
        6. Provide detailed reasoning for each decision

        Remember: Be conservative. Only swap when significantly better.
        """
        
        optimizer_content = types.Content(
            role="user", parts=[types.Part(text=optimizer_prompt)]
        )
        
        optimization_result = ""
        async for event in optimizer_runner.run_async(
            user_id=USER_ID, session_id=USER_ID + "_optimizer", new_message=optimizer_content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                optimization_result = event.content.parts[0].text
        
        try:
            optimization_data = json.loads(optimization_result)
        except json.JSONDecodeError:
            optimization_data = {"comparisons": [], "swaps_made": 0}
        
        # Return recommendations for user review (don't apply yet)
        return {
            "success": True,
            "optimization_analysis": optimization_data,
            "workflow_type": "experience_analysis",
            "message": f"Found {optimization_data.get('swaps_made', 0)} recommended swap(s). Review and accept to apply.",
            "requires_user_approval": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Smart optimization failed: {str(e)}")

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