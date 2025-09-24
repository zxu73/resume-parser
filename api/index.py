"""
Resume analysis API for Vercel deployment.
No database dependencies - pure AI-powered analysis.
"""

import os
import sys
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import PyPDF2
import docx
import io
import json
from typing import Dict, Any

# Add backend source to Python path for AI imports
backend_src = os.path.join(os.path.dirname(__file__), '..', 'backend', 'src')
if backend_src not in sys.path:
    sys.path.insert(0, backend_src)

app = FastAPI(title="Resume Analyzer API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResumeEvaluationRequest(BaseModel):
    resume_text: str
    job_description: str

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file."""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading PDF: {str(e)}")

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file."""
    try:
        doc = docx.Document(io.BytesIO(file_content))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading DOCX: {str(e)}")

# Initialize AI components (no database)
try:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from agent.agent import evaluation_agent, rating_agent
    
    # Set up session management (in-memory only, no database)
    session_service = InMemorySessionService()
    
    # Create runners for AI agents
    evaluation_runner = Runner(
        agent=evaluation_agent, 
        app_name="resume-optimizer-vercel", 
        session_service=session_service
    )
    rating_runner = Runner(
        agent=rating_agent, 
        app_name="resume-optimizer-vercel", 
        session_service=session_service
    )
    
    AI_ENABLED = True
except ImportError as e:
    print(f"AI components not available: {e}")
    AI_ENABLED = False

@app.get("/")
def root():
    return {"message": "Resume Analyzer API - Lightweight Version", "status": "healthy"}

@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Extract text from uploaded resume file."""
    try:
        content = await file.read()
        
        if file.filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(content)
        elif file.filename.lower().endswith('.docx'):
            text = extract_text_from_docx(content)
        elif file.filename.lower().endswith('.txt'):
            text = content.decode('utf-8')
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT.")
        
        return {
            "success": True,
            "analysis": text,
            "filename": file.filename
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/evaluate-resume")
async def evaluate_resume(request: ResumeEvaluationRequest):
    """AI-powered resume evaluation (no database required)."""
    try:
        if AI_ENABLED:
            # Use full AI analysis
            evaluation_result = await evaluation_runner.run(
                user_id="default_user",
                session_id="default_session",
                input_data={
                    "resume_text": request.resume_text,
                    "job_description": request.job_description
                }
            )
            
            rating_result = await rating_runner.run(
                user_id="default_user", 
                session_id="default_session",
                input_data={
                    "resume_text": request.resume_text,
                    "job_description": request.job_description,
                    "evaluation": evaluation_result
                }
            )
            
            return {
                "success": True,
                "message": "Resume analyzed with AI",
                "evaluation": evaluation_result,
                "rating": rating_result
            }
        else:
            # Fallback to basic keyword matching
            resume_words = set(request.resume_text.lower().split())
            job_words = set(request.job_description.lower().split())
            
            matching_keywords = resume_words.intersection(job_words)
            match_percentage = min(100, (len(matching_keywords) / max(len(job_words), 10)) * 100)
            
            return {
                "success": True,
                "message": "Resume analyzed with basic matching (AI unavailable)",
                "evaluation": {
                    "executive_summary": "Basic keyword analysis completed. AI components are not available in this deployment.",
                    "overall_score": min(10, max(1, int(match_percentage / 10))),
                    "job_match_percentage": int(match_percentage),
                    "matching_skills": list(matching_keywords)[:10],
                    "missing_skills": [],
                    "strengths": ["Resume processed successfully", "Keyword matching completed"],
                    "weaknesses": ["Limited analysis without AI components"],
                    "ats_compatibility": {"score": 7, "issues": [], "recommendations": []},
                    "section_analysis": {}
                },
                "rating": {
                    "detailed_ratings": {
                        "content_quality": {"score": 7},
                        "skills_match": {"score": int(match_percentage / 10)},
                        "experience_relevance": {"score": 6}
                    },
                    "priority_recommendations": [
                        {
                            "title": "Basic Analysis Only",
                            "description": "AI components unavailable. Only keyword matching performed.",
                            "priority": "Medium"
                        }
                    ],
                    "improved_resume": {
                        "contact_info": "Contact information preserved from original",
                        "work_experience": ["Work experience from resume"],
                        "education": "Education information preserved", 
                        "skills": list(matching_keywords)[:5],
                        "additional_sections": []
                    }
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "healthy", "ai_enabled": AI_ENABLED}
