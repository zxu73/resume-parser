# mypy: disable - error - code = "no-untyped-def,misc"
import pathlib
from fastapi import FastAPI, Response, Request, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from .agent import evaluation_agent, rating_agent
import json
import asyncio
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from typing import Dict, Any, List
import uuid

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

# Store threads in memory for LangGraph compatibility
threads: Dict[str, List[Dict[str, Any]]] = {}

# Store resume analysis results temporarily
resume_analyses: Dict[str, Dict[str, Any]] = {}
# --- End ADK Setup ---

# Pydantic models for request/response
class JobDescriptionRequest(BaseModel):
    job_description: str
    analysis_id: Optional[str] = None

class ResumeJobComparisonRequest(BaseModel):
    resume_analysis_id: str
    job_description: str

class QuickRatingRequest(BaseModel):
    resume_analysis_id: str

class ResumeEvaluationRequest(BaseModel):
    resume_text: str
    job_description: str

@asynccontextmanager
async def lifespan(app: FastAPI):
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
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],  # Frontend dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.post("/analyze-job-description")
async def analyze_job_description_endpoint(request: JobDescriptionRequest):
    """
    Analyze a job description to extract requirements and key information.
    """
    try:
        if not request.job_description.strip():
            raise HTTPException(status_code=400, detail="Job description cannot be empty")
        
        # Analyze the job description
        analysis_result = analyze_job_description(request.job_description)
        
        if not analysis_result.get("success"):
            raise HTTPException(status_code=500, detail=analysis_result.get("error", "Job description analysis failed"))
        
        return {
            "success": True,
            "analysis": analysis_result,
            "message": "Job description analyzed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job description analysis failed: {str(e)}")

@app.post("/compare-resume-job")
async def compare_resume_job_endpoint(request: ResumeJobComparisonRequest):
    """
    Compare a previously analyzed resume with a job description.
    Provides optimization suggestions and match analysis.
    """
    try:
        # Retrieve the resume analysis
        if request.resume_analysis_id not in resume_analyses:
            raise HTTPException(status_code=404, detail="Resume analysis not found. Please upload a resume first.")
        
        resume_data = resume_analyses[request.resume_analysis_id]
        resume_analysis = resume_data["analysis"]
        
        # Analyze the job description
        job_analysis = analyze_job_description(request.job_description)
        
        if not job_analysis.get("success"):
            raise HTTPException(status_code=500, detail=job_analysis.get("error", "Job description analysis failed"))
        
        # Compare resume with job requirements
        comparison_result = compare_resume_to_job(resume_analysis, job_analysis)
        
        if not comparison_result.get("success"):
            raise HTTPException(status_code=500, detail=comparison_result.get("error", "Comparison failed"))
        
        return {
            "success": True,
            "resume_filename": resume_data["filename"],
            "job_analysis": job_analysis,
            "comparison": comparison_result,
            "message": "Resume and job description compared successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")

@app.get("/resume-analysis/{analysis_id}")
async def get_resume_analysis(analysis_id: str):
    """
    Retrieve a previously stored resume analysis by ID.
    """
    if analysis_id not in resume_analyses:
        raise HTTPException(status_code=404, detail="Resume analysis not found")
    
    return {
        "success": True,
        "analysis_id": analysis_id,
        "data": resume_analyses[analysis_id]
    }

@app.post("/optimize-resume")
async def optimize_resume_with_agent(request: ResumeJobComparisonRequest):
    """
    Use the ADK agent to provide comprehensive resume optimization suggestions.
    This endpoint combines resume analysis, job analysis, and uses the agent's tools.
    """
    try:
        # Retrieve the resume analysis
        if request.resume_analysis_id not in resume_analyses:
            raise HTTPException(status_code=404, detail="Resume analysis not found. Please upload a resume first.")
        
        resume_data = resume_analyses[request.resume_analysis_id]
        resume_analysis = resume_data["analysis"]
        
        # Create a comprehensive prompt for the agent
        prompt = f"""
        Please provide comprehensive resume optimization suggestions based on this analysis:

        RESUME ANALYSIS:
        {resume_analysis.get('analysis', '')}

        JOB DESCRIPTION:
        {request.job_description}

        Please use your tools to:
        1. Analyze the job description for specific requirements
        2. Compare the resume against those requirements
        3. Search for current industry trends and salary insights for this role
        4. Provide specific, actionable optimization suggestions
        5. Include ATS optimization tips
        6. Suggest relevant keywords and skills to add

        Please provide a detailed, structured response with specific recommendations.
        """
        
        # Use the agent to process the request
        user_content = types.Content(
            role="user", parts=[types.Part(text=prompt)]
        )
        
        response_text = ""
        async for event in evaluation_runner.run_async(
            user_id=USER_ID, session_id=SESSION_ID, new_message=user_content
        ):
            if event.is_final_response() and event.content:
                response_text = event.content.parts[0].text
        
        return {
            "success": True,
            "resume_filename": resume_data["filename"],
            "optimization_suggestions": response_text,
            "message": "Resume optimization completed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume optimization failed: {str(e)}")

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
        
        # Step 1: Evaluation Agent
        evaluation_prompt = f"""
        Analyze this resume for the job description provided:

        RESUME:
        {request.resume_text}

        JOB DESCRIPTION:
        {request.job_description}

        SKILLS ANALYSIS DATA (USE THIS):
        {skills_analysis}

        CRITICAL: Use the skills analysis data above to provide specific insights:
        - Reference the match_percentage (e.g., "37.5% match")
        - List the matching_skills as strengths
        - Highlight the missing_skills as gaps
        - Use the skills analysis summary for context

        Provide a comprehensive evaluation covering:
        1. How well the resume matches the job requirements (use match_percentage)
        2. Key strengths (reference matching_skills) and weaknesses (reference missing_skills)
        3. ATS compatibility assessment
        4. Missing skills or experience gaps (use missing_skills list)
        5. Overall suitability for the role

        Be thorough and specific in your analysis with quantified data from the skills analysis.
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
        
        # Step 2: Rating Agent (using evaluation report from first agent)
        rating_prompt = f"""
        Based on the comprehensive evaluation from the first agent, provide ratings and generate an improved resume:

        EVALUATION REPORT FROM FIRST AGENT:
        {evaluation_report}

        SKILLS ANALYSIS DATA:
        {skills_analysis}

        ORIGINAL RESUME:
        {request.resume_text}

        JOB DESCRIPTION:
        {request.job_description}

        CRITICAL: Use the evaluation report above as your primary source, supported by skills analysis data:
        - Base your ratings on the evaluation report findings
        - Reference specific issues and strengths mentioned in the evaluation
        - Use skills analysis data for quantified insights (match_percentage, missing_skills)
        - Address the improvement areas identified in the evaluation

        Provide:
        1. DETAILED RATINGS (1-10) with specific justifications:
           - Content Quality: Quote specific weak phrases, identify missing metrics/numbers, point out vague language
           - ATS Compatibility: List exact missing keywords, identify formatting issues, note section problems
           - Skills Match: State exact match_percentage, list specific missing_skills and matching_skills from analysis
           - Experience Relevance: Identify specific experience gaps, weak job descriptions, missing achievements
        2. Top 3 priority recommendations with specific examples:
           - High Priority: Quote exact text to change and what to replace it with
           - Medium Priority: List specific missing keywords/skills to add and where
           - Low Priority: Identify exact formatting or structural improvements needed
        3. Complete improved resume with all sections (addressing evaluation feedback)

        Focus on creating a FULL improved resume that addresses the specific issues and gaps identified in the evaluation report.
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
                    
                    # Check if we have the complete improved resume
                    if "# IMPROVED RESUME" in rating_results and rating_results.count("Education") > 0:
                        print("DEBUG: Found complete resume structure")
                        
        except Exception as e:
            print(f"DEBUG: Rating stream error: {e}")
            
        print(f"DEBUG: Total rating results: {len(rating_results)} characters")
        
        # Check if response seems truncated
        if len(rating_results) > 0 and not rating_results.strip().endswith((".", "!", "?", "```")):
            print("WARNING: Response may be truncated")
        
        return {
            "success": True,
            "evaluation_report": evaluation_report,
            "rating_and_generation": rating_results,
            "workflow_type": "sequential_evaluation_and_rating",
            "message": "Resume evaluation and rating completed using sequential agents"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume evaluation failed: {str(e)}")

@app.post("/quick-resume-rating")
async def quick_resume_rating(request: QuickRatingRequest):
    """
    Provide a quick rating of a resume using the rating agent only.
    """
    try:
        # Retrieve the resume analysis
        if request.resume_analysis_id not in resume_analyses:
            raise HTTPException(status_code=404, detail="Resume analysis not found. Please upload a resume first.")
        
        resume_data = resume_analyses[request.resume_analysis_id]
        resume_analysis = resume_data["analysis"]
        
        # Create a simple prompt for quick rating
        prompt = f"""
        Please provide a quick rating of this resume:

        RESUME ANALYSIS:
        {resume_analysis.get('analysis', '')}

        Provide:
        1. Overall score (1-10)
        2. Key strengths (top 3)
        3. Key weaknesses (top 3)
        4. Quick recommendations (top 3)
        5. Market readiness assessment

        Keep the response concise but informative.
        """
        
        # Use the rating agent directly for quick rating
        user_content = types.Content(
            role="user", parts=[types.Part(text=prompt)]
        )
        
        response_text = ""
        async for event in rating_runner.run_async(
            user_id=USER_ID, session_id=SESSION_ID, new_message=user_content
        ):
            if event.is_final_response() and event.content:
                response_text = event.content.parts[0].text
        
        return {
            "success": True,
            "resume_filename": resume_data["filename"],
            "quick_rating": response_text,
            "message": "Quick resume rating completed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick resume rating failed: {str(e)}")

# === EXISTING ENDPOINTS (preserved) ===

@app.post("/threads")
async def create_thread(request: Request):
    """Creates a new thread for LangGraph compatibility."""
    body = await request.json()
    thread_id = str(uuid.uuid4())
    threads[thread_id] = []
    return {"thread_id": thread_id}


@app.post("/threads/{thread_id}/runs")
async def create_run(thread_id: str, request: Request):
    """Creates a run in a thread for LangGraph compatibility."""
    if thread_id not in threads:
        threads[thread_id] = []
    
    body = await request.json()
    # Extract the last message from the input
    messages = body.get("input", {}).get("messages", [])
    if messages:
        last_message = messages[-1]
        if last_message.get("type") == "human":
            # Get agent response using ADK
            try:
                user_content = types.Content(
                    role="user", parts=[types.Part(text=last_message["content"])]
                )
                response_text = ""
                async for event in evaluation_runner.run_async(
                    user_id=USER_ID, session_id=SESSION_ID, new_message=user_content
                ):
                    if event.is_final_response() and event.content:
                        response_text = event.content.parts[0].text
                
                # Add both human and AI messages to thread
                threads[thread_id].extend(messages)
                ai_message = {
                    "type": "ai",
                    "content": response_text,
                    "id": str(uuid.uuid4())
                }
                threads[thread_id].append(ai_message)
            except Exception as e:
                print(f"ERROR: Agent invocation failed: {e}")
                # Add error message
                ai_message = {
                    "type": "ai",
                    "content": f"Sorry, I encountered an error: {str(e)}",
                    "id": str(uuid.uuid4())
                }
                threads[thread_id].append(ai_message)
    
    run_id = str(uuid.uuid4())
    return {"run_id": run_id, "thread_id": thread_id}


@app.post("/threads/{thread_id}/runs/stream")
async def create_run_stream(thread_id: str, request: Request):
    """Creates a streaming run in a thread for LangGraph compatibility."""
    if thread_id not in threads:
        threads[thread_id] = []
    
    body = await request.json()
    print(f"DEBUG: Stream request body: {json.dumps(body, indent=2)}")
    
    # Extract the last message from the input
    messages = body.get("input", {}).get("messages", [])
    
    async def generate_stream():
        try:
            if messages:
                last_message = messages[-1]
                if last_message.get("type") == "human":
                    # Add human message to thread first
                    threads[thread_id].extend(messages)
                    
                    # Get agent response using ADK
                    user_content = types.Content(
                        role="user", parts=[types.Part(text=last_message["content"])]
                    )
                    response_text = ""
                    async for event in evaluation_runner.run_async(
                        user_id=USER_ID, session_id=SESSION_ID, new_message=user_content
                    ):
                        if event.is_final_response() and event.content:
                            response_text = event.content.parts[0].text
                    
                    print(f"DEBUG: Agent response: {response_text}")
                    
                    # Create AI message
                    ai_message = {
                        "type": "ai",
                        "content": response_text,
                        "id": str(uuid.uuid4())
                    }
                    threads[thread_id].append(ai_message)
                    
                    # Stream events in LangGraph format
                    yield f"event: messages\n"
                    yield f"data: {json.dumps({'messages': threads[thread_id]})}\n\n"
                    
                    # Send completion event
                    yield f"event: end\n"
                    yield f"data: {json.dumps({'status': 'completed'})}\n\n"
            
        except Exception as e:
            print(f"ERROR: Stream generation failed: {e}")
            error_message = {
                "type": "ai",
                "content": f"Sorry, I encountered an error: {str(e)}",
                "id": str(uuid.uuid4())
            }
            threads[thread_id].append(error_message)
            yield f"event: messages\n"
            yield f"data: {json.dumps({'messages': threads[thread_id]})}\n\n"
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.get("/threads/{thread_id}/runs/{run_id}")
async def get_run(thread_id: str, run_id: str):
    """Gets a run status for LangGraph compatibility."""
    if thread_id not in threads:
        return {"status": "error"}
    
    return {
        "status": "completed",
        "thread_id": thread_id,
        "run_id": run_id,
        "output": {"messages": threads[thread_id]}
    }


@app.get("/threads/{thread_id}")
async def get_thread(thread_id: str):
    """Gets thread messages for LangGraph compatibility."""
    if thread_id not in threads:
        return {"messages": []}
    return {"messages": threads[thread_id]}


@app.post("/threads/{thread_id}/history")
async def get_thread_history(thread_id: str, request: Request):
    """Gets thread history for LangGraph compatibility."""
    if thread_id not in threads:
        return {"messages": []}
    return {"messages": threads[thread_id]}


@app.get("/threads/{thread_id}/history")
async def get_thread_history_get(thread_id: str):
    """Gets thread history for LangGraph compatibility (GET method)."""
    if thread_id not in threads:
        return {"messages": []}
    return {"messages": threads[thread_id]}


@app.post("/invoke")
async def invoke(request: Request):
    """
    Invokes the agent with a user query. Supports both legacy format and AI SDK format.

    Args:
        request: The request object, containing the user query in the body.

    Returns:
        The agent's response (JSON for legacy, streaming for AI SDK).
    """
    body = await request.json()
    print(f"DEBUG: Received body: {json.dumps(body, indent=2)}")

    # Check if this is an AI SDK request (has 'messages' field)
    if "messages" in body:
        # AI SDK format - extract latest user message
        messages = body.get("messages", [])
        print(f"DEBUG: Messages array: {messages}")
        user_message = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                user_message = message.get("content", "")
                print(f"DEBUG: Found user message: '{user_message}'")
                break

        if not user_message:
            # No user message found, return error
            def generate_error_stream():
                yield '0:"No user message found in request"\n'
                yield 'd:{"finishReason":"stop"}\n'

            return StreamingResponse(
                generate_error_stream(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "x-vercel-ai-data-stream": "v1",
                    "Access-Control-Allow-Origin": "http://localhost:5173",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                },
            )

        # Stream the agent response in AI SDK data stream format
        async def generate_data_stream():
            try:
                user_content = types.Content(
                    role="user", parts=[types.Part(text=user_message)]
                )
                response_text = ""
                async for event in evaluation_runner.run_async(
                    user_id=USER_ID, session_id=SESSION_ID, new_message=user_content
                ):
                    if event.is_final_response() and event.content:
                        response_text = event.content.parts[0].text

                print(f"DEBUG: Response text: {response_text}")

                # Stream the response word by word for a nice typing effect
                words = response_text.split()
                if not words:
                    # Handle empty response
                    yield 'd:{"finishReason":"stop"}\n'
                    return

                for word in words:
                    # Text parts format: 0:"content"\n
                    yield f'0:"{word} "\n'

                # Finish message part
                yield 'd:{"finishReason":"stop"}\n'

            except Exception as e:
                print(f"ERROR: Agent invocation failed: {e}")
                # Stream error message
                yield f'0:"Sorry, I encountered an error while processing your request: {str(e)}"\n'
                yield 'd:{"finishReason":"stop"}\n'

        return StreamingResponse(
            generate_data_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "x-vercel-ai-data-stream": "v1",  # Required for AI SDK data stream
                "Access-Control-Allow-Origin": "http://localhost:5173",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
        )
    else:
        # Legacy format - direct query
        query = body.get("query")

        if not query:
            return Response(
                content=json.dumps({"error": "No query provided"}),
                media_type="application/json",
                status_code=400,
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:5173",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                },
            )

        try:
            user_content = types.Content(role="user", parts=[types.Part(text=query)])
            response_text = ""

            async for event in evaluation_runner.run_async(
                user_id=USER_ID, session_id=SESSION_ID, new_message=user_content
            ):
                if event.is_final_response() and event.content:
                    response_text = event.content.parts[0].text

            print(f"DEBUG: Final response text: {response_text}")

            return Response(
                content=json.dumps({"response": response_text}),
                media_type="application/json",
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:5173",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                },
            )
        except Exception as e:
            print(f"ERROR: Agent invocation failed: {e}")
            return Response(
                content=json.dumps({"error": f"Agent invocation failed: {str(e)}"}),
                media_type="application/json",
                status_code=500,
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:5173",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                },
            )


@app.options("/invoke")
async def invoke_options():
    """Handle preflight CORS requests for /invoke endpoint."""
    return Response(
        content="",
        headers={
            "Access-Control-Allow-Origin": "http://localhost:5173",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


def create_frontend_router(build_dir="../frontend/dist"):
    """Creates a router to serve the React frontend.

    Args:
        build_dir: Path to the React build directory relative to this file.

    Returns:
        A Starlette application serving the frontend.
    """
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        print(
            f"WARN: Frontend build directory not found or incomplete at {build_path}. Serving frontend will likely fail."
        )
        # Return a dummy router if build isn't ready
        from starlette.routing import Route

        async def dummy_frontend(request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )

        return Route("/{path:path}", endpoint=dummy_frontend)

    return StaticFiles(directory=build_path, html=True)


# Mount the frontend under /app to not conflict with the LangGraph API routes
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)