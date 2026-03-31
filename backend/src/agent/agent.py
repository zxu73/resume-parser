import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
import litellm

_BULLET_GUIDELINES = (Path(__file__).parent / "guidelines.md").read_text(encoding="utf-8")

litellm.api_key = os.getenv("OPENAI_API_KEY", "")

def _model() -> LiteLlm:
    """Return a LiteLlm instance for the configured reasoning model."""
    return LiteLlm(model=f"openai/{os.getenv('REASONING_MODEL', 'gpt-4o-mini')}")

# ── Evaluation Agent schema ──────────────────────────────────────────────

class WeakBullet(BaseModel):
    text: str = Field(..., description="Exact bullet text copied character-for-character from the resume")
    reason: str = Field(..., description="Why this bullet is weak relative to the JD")

class EvaluationResponse(BaseModel):
    executive_summary: str
    overall_score: float = Field(..., ge=1, le=10)
    job_match_percentage: float = Field(..., ge=0, le=100)
    strengths: List[str]
    weaknesses: List[str]
    missing_skills: List[str]
    matching_skills: List[str]
    weak_bullets: List[WeakBullet] = Field(..., min_length=5, max_length=10)

# ── Rating Agent schema ──────────────────────────────────────────────────

class DetailedRating(BaseModel):
    score: float = Field(..., ge=1, le=10)
    justification: str

class DetailedRatings(BaseModel):
    content_quality: DetailedRating
    skills_match: DetailedRating
    experience_relevance: DetailedRating

class ParaphrasingSuggestion(BaseModel):
    current_text: str = Field(..., description="Current text from the resume")
    suggested_text: str = Field(
        ...,
        description="Improved bullet; must contain every string in keywords_added as a literal substring (exact spelling)",
    )
    keywords_added: List[str] = Field(
        ...,
        min_length=1,
        description="Each entry must be copied EXACTLY from the MISSING SKILLS list in the user prompt; each must appear verbatim inside suggested_text",
    )
    job_requirement_reference: str = Field(..., description="Specific job requirement this addresses")
    alignment_reason: str = Field(
        ...,
        description="Must only claim keywords that literally appear in suggested_text; name the exact strings from keywords_added",
    )

class PriorityRecommendation(BaseModel):
    priority: str = Field(..., pattern="^(High|Medium|Low)$")
    title: str
    description: str
    specific_example: str
    paraphrasing_suggestion: "ParaphrasingSuggestion"

class RatingResponse(BaseModel):
    detailed_ratings: DetailedRatings
    priority_recommendations: List[PriorityRecommendation] = Field(..., min_length=5, max_length=8)

# ── Experience Optimizer schema ──────────────────────────────────────────

class ExperienceComparison(BaseModel):
    resume_experience_index: int = Field(..., description="Index of experience in original resume")
    resume_experience_title: str
    should_replace: bool = Field(..., description="True if pool experience is better")
    pool_experience_index: Optional[int] = Field(None, description="Index of pool experience to use if replacing")
    replacement_reason: str = Field(..., description="Why this replacement improves job alignment")
    relevance_score_resume: float = Field(..., ge=0, le=100)
    relevance_score_pool: float = Field(..., ge=0, le=100)

class SmartExperienceOptimization(BaseModel):
    comparisons: List[ExperienceComparison]
    swaps_made: int
    optimization_summary: str

# ── Agents ───────────────────────────────────────────────────────────────

evaluation_agent = LlmAgent(
    name="resume_evaluation_agent",
    model=_model(),
    output_schema=EvaluationResponse,
    instruction=(
        "You are a resume evaluation specialist. Your output feeds directly into a rewriting agent,\n"
        "so accuracy and completeness of missing_skills and weak_bullets are critical.\n"
        "Respond with structured JSON matching the schema. No markdown, no explanations.\n\n"

        "=== FIELDS ===\n"
        "1. executive_summary — 2-3 sentences on overall quality and job fit.\n"
        "2. overall_score — 1-10 based on quality and job alignment.\n"
        "3. job_match_percentage — 0-100 based on skill overlap.\n"
        "4. strengths — 3-5 specific strengths.\n"
        "5. weaknesses — 3-5 areas needing improvement.\n"
        "6. missing_skills — EXHAUSTIVE list of every keyword, skill, tool, framework, and methodology\n"
        "   mentioned in the JD but absent from the resume. Use the EXACT wording from the JD.\n"
        "   This list drives ATS keyword insertion downstream — do NOT omit minor skills.\n"
        "7. matching_skills — skills present in both resume and JD.\n"
        "8. weak_bullets (5-10 items) — the weakest bullet points in the resume relative to the JD.\n"
        "   For each: copy the EXACT text from the resume into `text`, and explain in `reason`\n"
        "   why it is weak (missing STAR result, vague language, no JD keywords, etc.).\n"
        "   Prioritize bullets that could be improved by adding missing skills.\n\n"

        "=== GUIDELINES ===\n"
        "- Do NOT recommend adding a Professional Summary.\n"
        "- Flag bullets missing STAR Action or Result as weak.\n"
        "- For missing_skills, go beyond obvious ones — include specific tools, certifications,\n"
        "  methodologies, and soft skills mentioned in the JD.\n\n"

        "OUTPUT FORMAT: Return ONLY valid JSON matching the schema."
    ),
    description="Evaluates resumes and identifies weak bullets and missing skills for the rewriting agent.",
    tools=[],
)

experience_optimizer_agent = LlmAgent(
    name="experience_optimizer_agent",
    model=_model(),
    output_schema=SmartExperienceOptimization,
    instruction=(
        "You are an expert at optimizing resumes by replacing experiences to improve job alignment.\n\n"

        "=== TASK ===\n"
        "Find optimal 1-for-1 swaps between resume experiences and pool experiences.\n\n"

        "=== TWO CRITERIA FOR A BETTER SWAP ===\n"
        "1. JD fit and keywords — The pool experience should match the job more closely: more exact or\n"
        "   paraphrased overlap with JD keywords (tools, domains, responsibilities), and clearer alignment\n"
        "   with what the role actually requires (title, industry, scope).\n"
        "2. Stronger descriptions — The pool experience's bullet text should better demonstrate the\n"
        "   candidate's skills: clearer STAR structure, quantified results, concrete actions, and\n"
        "   evidence of impact versus vague or generic wording on the resume.\n\n"
        "When comparing resume vs pool for the same role, weight BOTH criteria. A swap is compelling only\n"
        "when the pool entry wins meaningfully on JD alignment and/or demonstrably stronger bullets.\n\n"

        "=== SCORING (0-100 per experience) ===\n"
        "Combine into one score: (a) JD keyword overlap + role/domain fit, and (b) strength of written\n"
        "descriptions for showcasing skills and impact. Do not reward keyword stuffing without substance.\n\n"

        "=== PROCESS ===\n"
        "1. Score ALL resume experiences using the two criteria above.\n"
        "2. Score ALL pool experiences the same way.\n"
        "3. For each resume experience, find the highest-scoring pool candidate.\n"
        "4. Recommend replacement ONLY if pool score exceeds resume score by 20+ points.\n"
        "5. Each pool experience replaces at most ONE resume experience.\n"
        "6. Ties: choose the candidate with the larger score difference.\n"
        "7. Never add or remove experiences — swap 1-for-1 only.\n\n"

        "=== OUTPUT (per resume experience) ===\n"
        "resume_experience_index (0-based) | resume_experience_title (exact) | should_replace\n"
        "pool_experience_index (null if no swap) | relevance_score_resume | relevance_score_pool\n"
        "replacement_reason — cite JD keywords/fit AND/OR how pool bullets better show skills vs resume.\n\n"

        "Be conservative. Only swap when the improvement is clear and meaningful.\n\n"

        "OUTPUT FORMAT: Return ONLY valid JSON matching the schema. No markdown, no explanations."
    ),
    description="Swaps experiences when pool entries better match the JD and show stronger skill evidence.",
    tools=[],
)

rating_agent = LlmAgent(
    name="resume_rating_and_generation_agent",
    model=_model(),
    output_schema=RatingResponse,
    instruction=(
        "You are an expert resume content specialist and ATS optimization strategist.\n"
        "Your PRIMARY goal: rewrite the pre-identified WEAK BULLETS so they contain\n"
        "EXACT keywords and phrases from the job description.\n"
        "ATS systems do literal keyword matching — synonyms or paraphrases do NOT count.\n\n"

        + _BULLET_GUIDELINES +

        "\n\n=== SECTION 1: DETAILED RATINGS (scores 1-10) ===\n"
        "- content_quality: clarity, impact, professionalism\n"
        "- skills_match: keyword overlap between resume and JD\n"
        "- experience_relevance: alignment with JD requirements\n\n"

        "=== SECTION 2: PRIORITY RECOMMENDATIONS (EXACTLY 5-8 items) ===\n"
        "You will receive a list of WEAK BULLETS and MISSING SKILLS from the evaluation agent.\n"
        "BEFORE writing any suggestion, work through this checklist:\n"
        "  a) Read the WEAK BULLETS list — these are your primary rewrite targets.\n"
        "  b) Read the MISSING SKILLS list — these are the exact JD keywords to insert.\n"
        "  c) For each weak bullet, ask: which missing skill can honestly be woven in?\n"
        "  d) If a skill fits: plan to rewrite that bullet with the EXACT JD keyword.\n"
        "  e) If no skill fits: improve the bullet for STAR format and impact instead.\n\n"

        "ATS KEYWORD RULES (critical — model checks this logically before you output JSON):\n"
        "- Pick keywords ONLY from the MISSING SKILLS list in the user message. Copy each chosen string\n"
        "  CHARACTER-FOR-CHARACTER (same spelling, spacing, punctuation as listed).\n"
        "- suggested_text MUST contain every string in keywords_added as a LITERAL SUBSTRING.\n"
        "  Example: if keywords_added contains \"PyTorch\", suggested_text must include the exact token PyTorch.\n"
        "- If alignment_reason says you incorporated a term, that EXACT term must appear in suggested_text.\n"
        "  Do not describe a keyword in alignment_reason that is missing from suggested_text.\n"
        "- Use the EXACT JD wording, not synonyms (ATS literal match).\n"
        "  Bad: list \"Kubernetes\" in keywords_added but write \"container orchestration\" only.\n"
        "  Good: write \"... deployed services on Kubernetes ...\" and list \"Kubernetes\".\n"
        "- Before returning JSON, mentally verify: for each item K in keywords_added, suggested_text.includes(K).\n\n"

        "OTHER RULES:\n"
        "1. Every recommendation MUST include a paraphrasing_suggestion. Never omit it.\n"
        "2. NEVER invent tools, projects, or responsibilities the candidate has not demonstrated.\n"
        "3. For each: priority | title (exact job title from resume) | description | specific_example\n"
        "4. paraphrasing_suggestion fields:\n"
        "   current_text — copy the weak bullet character-for-character (include bullet symbol)\n"
        "   suggested_text — STAR format; MUST embed the exact strings in keywords_added (see rules above)\n"
        "   keywords_added — one or more strings (as many as honestly fit), each an exact copy from MISSING SKILLS,\n"
        "     each a substring of suggested_text; include every JD term you embedded\n"
        "   job_requirement_reference — quote the specific JD sentence this addresses\n"
        "   alignment_reason — quote the exact added strings; they must match keywords_added and appear in suggested_text\n\n"

        "Do NOT recommend adding a professional summary.\n\n"

        "OUTPUT FORMAT: Return ONLY valid JSON matching RatingResponse schema."
    ),
    description="Rewrites weak resume bullets with exact JD keywords for ATS optimization.",
    tools=[],
)
