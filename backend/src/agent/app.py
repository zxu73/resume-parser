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
from google.genai import types   # ADK still needs genai types for Content/Part
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

# Store uploaded files on disk so they survive hot-reloads and server restarts
import tempfile, os as _os
_STORE_DIR = pathlib.Path(tempfile.gettempdir()) / "resume_parser_files"
_STORE_DIR.mkdir(parents=True, exist_ok=True)


def _pdf_path(file_id: str) -> pathlib.Path:
    return _STORE_DIR / f"{file_id}.pdf"


def _doc_path(file_id: str) -> pathlib.Path:
    return _STORE_DIR / f"{file_id}.docx"


def _store_pdf(file_id: str, data: bytes) -> None:
    _pdf_path(file_id).write_bytes(data)


def _store_doc(file_id: str, data: bytes) -> None:
    _doc_path(file_id).write_bytes(data)


def _load_pdf(file_id: str) -> bytes | None:
    p = _pdf_path(file_id)
    return p.read_bytes() if p.exists() else None


def _load_doc(file_id: str) -> bytes | None:
    p = _doc_path(file_id)
    return p.read_bytes() if p.exists() else None

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

        # Persist file to disk so it survives hot-reloads
        is_pdf = file.content_type == "application/pdf"
        is_docx = file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if is_pdf:
            _store_pdf(analysis_id, content)
        elif is_docx:
            _store_doc(analysis_id, content)

        return {
            "success": True,
            "analysis_id": analysis_id,
            "pdf_id": analysis_id if is_pdf else None,
            "doc_id": analysis_id if is_docx else None,
            "filename": file.filename,
            "file_size": len(content),
            "analysis": analysis_result.get("analysis", ""),
            "extracted_text": analysis_result.get("extracted_text", ""),
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

        # ── Step 1: Evaluation Agent ─────────────────────────────────────
        evaluation_prompt = f"""
        RESUME:
        {request.resume_text}

        JOB DESCRIPTION:
        {request.job_description}
        """

        evaluation_content = types.Content(
            role="user", parts=[types.Part(text=evaluation_prompt)]
        )

        request_session_id = str(uuid.uuid4())
        await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=request_session_id
        )

        evaluation_report = ""
        async for event in evaluation_runner.run_async(
            user_id=USER_ID, session_id=request_session_id, new_message=evaluation_content
        ):
            if event.content and event.content.parts:
                evaluation_report += event.content.parts[0].text

        print(f"DEBUG: Evaluation report: {len(evaluation_report)} chars")

        try:
            evaluation_data = json.loads(evaluation_report)
            print("DEBUG: Parsed evaluation JSON OK")
        except json.JSONDecodeError as e:
            print(f"DEBUG: Failed to parse evaluation JSON: {e}")
            evaluation_data = {"raw_text": evaluation_report}

        # ── Override job_match_percentage with deterministic calculation ──
        matching = evaluation_data.get("matching_skills", [])
        missing = evaluation_data.get("missing_skills", [])
        total_skills = len(matching) + len(missing)
        evaluation_data["job_match_percentage"] = (
            round(len(matching) / total_skills * 100, 1) if total_skills > 0 else 0.0
        )

        # ── Build structured context for rating agent ────────────────────
        missing_skills: list = evaluation_data.get("missing_skills", [])

        missing_block = "\n".join(
            f"  {i+1}. {s}" for i, s in enumerate(missing_skills)
        ) if missing_skills else "(none identified)"

        # ── Step 2: Rating Agent ─────────────────────────────────────────
        rating_prompt = f"""
TASK: Visit every bullet in the resume. For each, decide: add missing keywords (Rule A),
improve STAR format (Rule B), or skip.

==================== JOB DESCRIPTION ====================
{request.job_description}

==================== ORIGINAL RESUME TEXT ====================
Copy current_text from here EXACTLY — character-for-character.

{request.resume_text}

==================== MISSING JD KEYWORDS ====================
{missing_block}

==================== EVALUATION CONTEXT ====================
Strengths: {json.dumps(evaluation_data.get("strengths", []))}
Weaknesses: {json.dumps(evaluation_data.get("weaknesses", []))}

INSTRUCTIONS:
- Visit every bullet in the resume, one by one
- If a missing skill can be plausibly added, rewrite in STAR format with the keyword → keyword_suggestions
- If no keyword fits but the bullet can be improved (vague, weak verb, no result), rewrite in STAR format → star_suggestions
- If neither, skip
- current_text must be copied character-for-character from the resume
- Each bullet appears in at most one section
"""

        rating_content = types.Content(
            role="user", parts=[types.Part(text=rating_prompt)]
        )

        rating_results = ""
        try:
            async for event in rating_runner.run_async(
                user_id=USER_ID, session_id=request_session_id, new_message=rating_content
            ):
                if event.content and event.content.parts:
                    rating_results += event.content.parts[0].text
        except Exception as e:
            print(f"DEBUG: Rating stream error: {e}")

        print(f"DEBUG: Rating results: {len(rating_results)} chars")

        try:
            rating_data = json.loads(rating_results)
            print("DEBUG: Parsed rating JSON OK")
        except json.JSONDecodeError as e:
            print(f"DEBUG: Failed to parse rating JSON: {e}")
            rating_data = {"raw_text": rating_results}

        # ── Post-processing: sanitize keyword claims ────────────────
        import re as _re

        def _sanitize_rec(rec: dict) -> None:
            """Clean up alignment_reason to remove claims about keywords not in suggested_text.
            Does NOT modify keywords_added — section routing uses the original LLM-reported list."""
            sug = rec.get("paraphrasing_suggestion")
            if not sug:
                return
            suggested_lower = sug.get("suggested_text", "").lower()
            original_kw = sug.get("keywords_added", [])
            removed_kw = [kw for kw in original_kw if kw.lower() not in suggested_lower]
            reason = sug.get("alignment_reason", "")
            for kw in removed_kw:
                reason = reason.replace(f"'{kw}'", "").replace(f'"{kw}"', "").replace(kw, "")
            reason = _re.sub(r"\s*,\s*,", ",", reason)
            reason = _re.sub(r"\s*and\s*and\s*", " and ", reason)
            reason = _re.sub(r"\s{2,}", " ", reason).strip()
            reason = _re.sub(r"^[,\s]+|[,\s]+$", "", reason)
            sug["alignment_reason"] = reason
            if removed_kw:
                print(f"DEBUG: Cleaned alignment_reason for missing keywords {removed_kw} in '{rec.get('title', '')}'")

        for rec in rating_data.get("keyword_suggestions", []):
            _sanitize_rec(rec)
        for rec in rating_data.get("star_suggestions", []):
            _sanitize_rec(rec)

        # ── Move keyword entries with empty keywords_added to star_suggestions
        # Uses original LLM-reported keywords_added (not stripped) for routing.
        # Only items where LLM itself said keywords_added=[] belong in star_suggestions.
        real_keyword = []
        for rec in rating_data.get("keyword_suggestions", []):
            sug = rec.get("paraphrasing_suggestion", {})
            if sug.get("keywords_added"):  # non-empty list = LLM claimed keyword insertion
                real_keyword.append(rec)
            else:
                rating_data.setdefault("star_suggestions", []).append(rec)
                print(f"DEBUG: Moved '{rec.get('title', '')}' to star_suggestions (LLM reported empty keywords_added)")
        rating_data["keyword_suggestions"] = real_keyword

        # ── Deduplicate: drop star entries whose bullet is already in keyword section
        keyword_texts = {
            rec.get("paraphrasing_suggestion", {}).get("current_text", "").strip()
            for rec in rating_data.get("keyword_suggestions", [])
        }
        original_count = len(rating_data.get("star_suggestions", []))
        rating_data["star_suggestions"] = [
            rec for rec in rating_data.get("star_suggestions", [])
            if rec.get("paraphrasing_suggestion", {}).get("current_text", "").strip()
            not in keyword_texts
        ]
        removed = original_count - len(rating_data.get("star_suggestions", []))
        if removed:
            print(f"DEBUG: Removed {removed} overlapping star_suggestion(s)")

        return {
            "success": True,
            "structured_evaluation": evaluation_data,
            "structured_rating": rating_data,
            "workflow_type": "sequential_evaluation_and_rating",
            "message": "Resume evaluation and rating completed"
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
        
        optimizer_session_id = str(uuid.uuid4())
        await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=optimizer_session_id
        )

        optimization_result = ""
        async for event in optimizer_runner.run_async(
            user_id=USER_ID, session_id=optimizer_session_id, new_message=optimizer_content
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

# === EXPERIENCE SWAP ON DOCX ===

class ExperienceSwap(BaseModel):
    resume_experience_title: str
    pool_title: str
    pool_company: str = ""
    pool_duration: str = ""
    pool_description: str = ""

class ApplySwapsRequest(BaseModel):
    doc_id: str
    swaps: list[ExperienceSwap]

@app.post("/apply-swaps-docx")
async def apply_swaps_docx(request: ApplySwapsRequest):
    """Apply accepted experience swaps to the Word document.

    For each swap, finds the section headed by the old experience title
    and replaces it with the pool experience content.  Returns a new
    doc_id pointing to the modified file so the frontend can preview it.
    """
    import re as _re
    from docx import Document as DocxDocument
    import io

    data = _load_doc(request.doc_id)
    if not data:
        raise HTTPException(status_code=404, detail="Document not found")

    _W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    _XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

    def norm(t: str) -> str:
        return _re.sub(r"\s+", " ", t).strip()

    def para_full_text(para) -> str:
        return "".join(
            t.text or "" for t in para._element.iter(f"{{{_W_NS}}}t")
        )

    def write_para(para, new_text: str) -> None:
        all_t = list(para._element.iter(f"{{{_W_NS}}}t"))
        if not all_t:
            return
        all_t[0].text = new_text
        all_t[0].set(_XML_SPACE, "preserve")
        for t in all_t[1:]:
            t.text = ""

    doc = DocxDocument(io.BytesIO(data))
    paras = doc.paragraphs

    for swap in request.swaps:
        old_title_norm = norm(swap.resume_experience_title).lower()

        # Find the paragraph that contains the old experience title
        start_idx = None
        for i, p in enumerate(paras):
            if old_title_norm in norm(para_full_text(p)).lower():
                start_idx = i
                break

        if start_idx is None:
            continue

        # Determine the extent of this experience block:
        # from the title paragraph to the paragraph before the next
        # section/experience heading (heuristic: next paragraph whose
        # font is bold or whose style name contains "Heading", or
        # a blank line followed by another bold/heading paragraph).
        end_idx = start_idx + 1
        for j in range(start_idx + 1, len(paras)):
            text = para_full_text(paras[j]).strip()
            if not text:
                end_idx = j
                continue
            # Check if this paragraph looks like a new heading
            is_bold = any(
                r.bold for r in paras[j].runs if r.text.strip()
            ) if paras[j].runs else False
            style_name = (paras[j].style.name or "").lower()
            is_heading = "heading" in style_name
            if (is_bold or is_heading) and j > start_idx + 1:
                break
            end_idx = j + 1

        # Build replacement lines
        new_lines = [swap.pool_title]
        meta_parts = [p for p in [swap.pool_company, swap.pool_duration] if p]
        if meta_parts:
            new_lines.append(" | ".join(meta_parts))
        if swap.pool_description:
            for bullet in swap.pool_description.split("\n"):
                b = bullet.strip()
                if b:
                    new_lines.append(b)

        # Write replacement: reuse existing paragraphs where possible,
        # clear extras
        for k in range(start_idx, end_idx):
            line_idx = k - start_idx
            if line_idx < len(new_lines):
                write_para(paras[k], new_lines[line_idx])
            else:
                write_para(paras[k], "")

    # Save to a NEW doc_id so the original is preserved
    buf = io.BytesIO()
    doc.save(buf)
    new_bytes = buf.getvalue()

    new_doc_id = f"swapped_{request.doc_id}"
    _store_doc(new_doc_id, new_bytes)

    # Also extract text from the modified doc for the evaluation step
    from .tools import extract_text_from_docx
    modified_text = extract_text_from_docx(new_bytes)

    return {
        "success": True,
        "doc_id": new_doc_id,
        "modified_resume_text": modified_text,
    }


# === FILE VIEWER / DOWNLOAD ENDPOINTS ===

@app.get("/resume-pdf/{pdf_id}")
async def serve_resume_pdf(pdf_id: str):
    """Serve the original uploaded PDF so the frontend can display it."""
    data = _load_pdf(pdf_id)
    if not data:
        raise HTTPException(status_code=404, detail="PDF not found")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/resume-doc/{doc_id}")
async def serve_resume_doc(doc_id: str):
    """Serve the original uploaded Word document so the frontend can render it."""
    data = _load_doc(doc_id)
    if not data:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Cache-Control": "no-store"},
    )


class TextReplacement(BaseModel):
    current_text: str
    suggested_text: str


class ModifyPDFRequest(BaseModel):
    pdf_id: str
    replacements: list[TextReplacement]


def _apply_replacement(page, current_text: str, suggested_text: str) -> bool:
    """
    Find current_text on a PDF page and replace it with suggested_text, preserving
    the original font size and color.

    Strategy:
    1. Use the first 40 chars of the (normalised) current_text as a short anchor for
       page.search_for(), which is reliable for short strings even across ligatures.
    2. Walk page.get_text("dict") spans to collect every span that belongs to the
       full bullet (potentially spanning multiple lines).
    3. Union all their bboxes into one combined rect.
    4. Extract font size + colour from the first matching span.
    5. Apply a single add_redact_annot on the combined rect so the whole multi-line
       bullet is whited out and the new text is drawn in the same size/colour.
    """
    import fitz
    import re

    def norm(t: str) -> str:
        return re.sub(r"\s+", " ", t).strip()

    norm_current = norm(current_text)
    # Strip leading bullet / dash symbols for the anchor search
    anchor_clean = re.sub(r"^[•·\-\*\s]+", "", norm_current)
    anchor = anchor_clean[:40].strip()
    if not anchor:
        return False

    instances = page.search_for(anchor)
    if not instances:
        return False

    anchor_rect = instances[0]

    # Walk all spans to find those belonging to this bullet
    text_dict = page.get_text("dict")
    collected_spans = []
    accumulated = ""
    collecting = False
    font_size = 10.0
    font_color_raw = 0  # integer packed RGB

    for block in text_dict.get("blocks", []):
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                span_rect = fitz.Rect(span["bbox"])

                # Start collecting once we hit the anchor span
                if not collecting and span_rect.intersects(anchor_rect):
                    collecting = True
                    font_size = span["size"]
                    font_color_raw = span["color"]

                if collecting:
                    collected_spans.append(span)
                    accumulated += span["text"]

                    # Stop once we have matched enough text
                    if norm_current in norm(accumulated):
                        break
            if collected_spans and norm_current in norm(accumulated):
                break
        if collected_spans and norm_current in norm(accumulated):
            break

    if not collected_spans:
        # Fallback: use just the anchor rect with default font properties
        collected_spans = [{"bbox": anchor_rect, "size": font_size, "color": 0}]

    # Build the union of all collected span bboxes
    combined = fitz.Rect(collected_spans[0]["bbox"])
    for span in collected_spans[1:]:
        combined = combined | fitz.Rect(span["bbox"])

    # Convert packed-int colour to (r, g, b) floats (PyMuPDF stores as 0xRRGGBB int)
    c = font_color_raw
    rgb = ((c >> 16) / 255.0, ((c >> 8) & 0xFF) / 255.0, (c & 0xFF) / 255.0)

    page.add_redact_annot(
        combined,
        text=suggested_text,
        fontsize=round(font_size, 1),
        text_color=rgb,
        align=0,  # left-align
    )
    return True


@app.post("/download-modified-pdf")
async def download_modified_pdf(request: ModifyPDFRequest):
    """Apply approved text replacements to the original PDF and return the modified file."""
    data = _load_pdf(request.pdf_id)
    if not data:
        raise HTTPException(status_code=404, detail="PDF not found")

    import fitz  # pymupdf
    doc = fitz.open(stream=data, filetype="pdf")

    for page in doc:
        changed = False
        for rep in request.replacements:
            if _apply_replacement(page, rep.current_text, rep.suggested_text):
                changed = True
        if changed:
            page.apply_redactions()

    return Response(
        content=doc.tobytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=improved-resume.pdf"},
    )


class ModifyDocxRequest(BaseModel):
    doc_id: str
    replacements: list[TextReplacement]


@app.post("/download-modified-docx")
async def download_modified_docx(request: ModifyDocxRequest):
    """Apply approved text replacements to the original Word document and return it."""
    import re
    from docx import Document as DocxDocument
    import io

    data = _load_doc(request.doc_id)
    if not data:
        raise HTTPException(status_code=404, detail="Document not found")

    _W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    _XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

    def norm(t: str) -> str:
        return re.sub(r"\s+", " ", t).strip()

    _BULLET_RE = re.compile(r"^[\s•·–—\u2013\u2014\u2022\u25aa\u25ba*○▪►◆▸\-]+")

    def strip_bullet(t: str) -> str:
        return _BULLET_RE.sub("", t).strip()

    def para_full_text(para) -> str:
        """Get ALL text in the paragraph, including text inside
        hyperlinks, smart tags, and other nested elements that
        para.runs / para.text might miss."""
        p_elem = para._element
        return "".join(
            t.text or "" for t in p_elem.iter(f"{{{_W_NS}}}t")
        )

    def write_para(para, new_text: str) -> None:
        """Replace ALL text in the paragraph with new_text.

        Finds every <w:t> element (including those nested inside
        <w:hyperlink>, <w:smartTag>, etc.), puts the full new text in
        the first one, and blanks out the rest.  This guarantees no
        leftover text from hidden nested elements.
        """
        p_elem = para._element
        all_t = list(p_elem.iter(f"{{{_W_NS}}}t"))
        if not all_t:
            return
        all_t[0].text = new_text
        all_t[0].set(_XML_SPACE, "preserve")
        for t in all_t[1:]:
            t.text = ""

    def is_match(body: str, current: str) -> bool:
        """Check if a paragraph body matches current_text (exact or anchor)."""
        if current in body:
            return True
        anchor = current[:40]
        if len(anchor) >= 20 and anchor in body:
            return True
        return False

    def apply_replacement(paras: list, current: str, suggested: str) -> bool:
        """Find the paragraph(s) matching current_text, replace with
        suggested_text, and clear any continuation paragraphs.

        A single resume bullet can span multiple Word paragraphs
        (Word wraps long text into continuation <w:p> elements).
        After replacing the first matched paragraph, we scan forward
        and clear subsequent paragraphs whose text appears inside the
        original current_text — these are leftover continuations.
        """
        norm_current = strip_bullet(norm(current))
        norm_suggested = strip_bullet(norm(suggested))

        if not norm_current:
            return False

        for i, para in enumerate(paras):
            body = strip_bullet(norm(para_full_text(para)))
            if not body:
                continue

            if not is_match(body, norm_current):
                continue

            # Found the starting paragraph — replace it
            write_para(para, norm_suggested)

            # Remove continuation paragraphs that are leftover line-wrap fragments.
            # Walk forward and delete (not blank) every paragraph whose text is
            # a substring of the original bullet — leaving no empty <w:p> behind.
            j = i + 1
            while j < len(paras):
                cont = strip_bullet(norm(para_full_text(paras[j])))
                if len(cont) >= 8 and cont in norm_current:
                    elem = paras[j]._element
                    elem.getparent().remove(elem)
                    j += 1
                else:
                    break

            return True

        return False

    doc = DocxDocument(io.BytesIO(data))

    for rep in request.replacements:
        if apply_replacement(list(doc.paragraphs), rep.current_text, rep.suggested_text):
            continue
        # Also search inside tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if apply_replacement(list(cell.paragraphs), rep.current_text, rep.suggested_text):
                        break

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=improved-resume.docx"},
    )


# === FRONTEND STATIC FILES ===
# Mount React frontend after all API routes (must be last)

import os
from pathlib import Path

frontend_dist_path = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"

if frontend_dist_path.exists() and (frontend_dist_path / "index.html").exists():
    from fastapi.responses import HTMLResponse

    from fastapi.responses import FileResponse

    # Serve hashed assets (js/css/images) — these are safe to cache
    app.mount("/assets", StaticFiles(directory=frontend_dist_path / "assets"), name="assets")

    # Serve other static files from dist root (e.g. vite.svg, favicon.ico)
    @app.get("/{file_name:path}")
    async def serve_spa(file_name: str):
        # If the file exists in dist, serve it directly
        file_path = frontend_dist_path / file_name
        if file_name and file_path.is_file() and file_path.name != "index.html":
            return FileResponse(file_path)
        # Otherwise serve index.html with no-cache for SPA routing
        return HTMLResponse(
            content=(frontend_dist_path / "index.html").read_text(),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    print(f"✅ Frontend mounted from: {frontend_dist_path}")
else:
    print(f"⚠️ Frontend build not found at: {frontend_dist_path}")
    
    @app.get("/")
    async def root():
        return {"message": "Resume Analyzer API", "status": "Backend running", "note": "Frontend build not found"}