import os
from typing import List, Optional
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.genai import types

# Define Pydantic models for structured response schemas (ADK requirement)

class SectionAnalysisItem(BaseModel):
    score: float = Field(..., ge=1, le=10)
    feedback: str

class SectionAnalysis(BaseModel):
    contact_info: SectionAnalysisItem
    work_experience: SectionAnalysisItem
    education: SectionAnalysisItem
    skills: SectionAnalysisItem

class ATSCompatibility(BaseModel):
    score: float = Field(..., ge=1, le=10)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

class EvaluationResponse(BaseModel):
    executive_summary: str
    overall_score: float = Field(..., ge=1, le=10)
    job_match_percentage: float = Field(..., ge=0, le=100)
    section_analysis: SectionAnalysis
    strengths: List[str]
    weaknesses: List[str]
    missing_skills: List[str]
    matching_skills: List[str]
    ats_compatibility: ATSCompatibility

class DetailedRating(BaseModel):
    score: float = Field(..., ge=1, le=10)
    justification: str
    specific_issues: Optional[List[str]] = None
    missing_keywords: Optional[List[str]] = None
    formatting_issues: Optional[List[str]] = None
    match_percentage: Optional[float] = None
    matching_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    gaps: Optional[List[str]] = None

class DetailedRatings(BaseModel):
    content_quality: DetailedRating
    ats_compatibility: DetailedRating
    skills_match: DetailedRating
    experience_relevance: DetailedRating

class PriorityRecommendation(BaseModel):
    priority: str = Field(..., pattern="^(High|Medium|Low)$")
    title: str
    description: str
    specific_example: str
    paraphrasing_suggestion: Optional["ParaphrasingSuggestion"] = None

class ParaphrasingSuggestion(BaseModel):
    current_text: str = Field(..., description="Current text from the resume")
    suggested_text: str = Field(..., description="Improved text aligned with job requirements")
    job_requirement_reference: str = Field(..., description="Specific job requirement this addresses")
    alignment_reason: str = Field(..., description="Why this change improves job alignment")

class ImprovedResume(BaseModel):
    contact_info: str
    work_experience: List[str]
    education: str
    skills: List[str]
    additional_sections: List[str] = Field(default_factory=list)

class RatingResponse(BaseModel):
    detailed_ratings: DetailedRatings
    priority_recommendations: List[PriorityRecommendation] = Field(..., max_length=7)
    improved_resume: Optional[ImprovedResume] = None  # Optional - frontend applies recommendations to original

# Define structured response schemas for UI integration (keeping for reference)
EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {
            "type": "string",
            "description": "High-level summary of resume quality and job fit"
        },
        "overall_score": {
            "type": "number",
            "minimum": 1,
            "maximum": 10,
            "description": "Overall resume score out of 10"
        },
        "job_match_percentage": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "Percentage match with job requirements"
        },
                    "section_analysis": {
                "type": "object",
                "properties": {
                    "contact_info": {"type": "object", "properties": {"score": {"type": "number"}, "feedback": {"type": "string"}}},
                    "work_experience": {"type": "object", "properties": {"score": {"type": "number"}, "feedback": {"type": "string"}}},
                    "education": {"type": "object", "properties": {"score": {"type": "number"}, "feedback": {"type": "string"}}},
                    "skills": {"type": "object", "properties": {"score": {"type": "number"}, "feedback": {"type": "string"}}}
                }
            },
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of resume strengths"
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of areas needing improvement"
        },
        "missing_skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Skills required by job but missing from resume"
        },
        "matching_skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Skills that match job requirements"
        },
        "ats_compatibility": {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 1, "maximum": 10},
                "issues": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    "required": ["executive_summary", "overall_score", "job_match_percentage", "section_analysis", "strengths", "weaknesses", "ats_compatibility"]
}

RATING_SCHEMA = {
    "type": "object",
    "properties": {
        "detailed_ratings": {
            "type": "object",
            "properties": {
                "content_quality": {
                    "type": "object",
                    "properties": {
                        "score": {"type": "number", "minimum": 1, "maximum": 10},
                        "justification": {"type": "string"},
                        "specific_issues": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "ats_compatibility": {
                    "type": "object",
                    "properties": {
                        "score": {"type": "number", "minimum": 1, "maximum": 10},
                        "justification": {"type": "string"},
                        "missing_keywords": {"type": "array", "items": {"type": "string"}},
                        "formatting_issues": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "skills_match": {
                    "type": "object",
                    "properties": {
                        "score": {"type": "number", "minimum": 1, "maximum": 10},
                        "match_percentage": {"type": "number"},
                        "matching_skills": {"type": "array", "items": {"type": "string"}},
                        "missing_skills": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "experience_relevance": {
                    "type": "object",
                    "properties": {
                        "score": {"type": "number", "minimum": 1, "maximum": 10},
                        "justification": {"type": "string"},
                        "gaps": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        },
        "priority_recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "specific_example": {"type": "string"}
                }
            },
            "maxItems": 5
        },
                    "improved_resume": {
                "type": "object",
                "properties": {
                    "contact_info": {"type": "string"},
                    "work_experience": {"type": "array", "items": {"type": "string"}},
                    "education": {"type": "string"},
                    "skills": {"type": "array", "items": {"type": "string"}},
                    "additional_sections": {"type": "array", "items": {"type": "string"}}
                }
            }
    },
    "required": ["detailed_ratings", "priority_recommendations", "improved_resume"]
}

# First agent: Resume Evaluation Agent
evaluation_agent = LlmAgent(
    name="resume_evaluation_agent",
    model=os.getenv("REASONING_MODEL", "gemini-2.5-flash"),
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=12000,  # Increased token limit for comprehensive analysis
        temperature=0.0,         # Optional: control randomness
    ),
    output_schema=EvaluationResponse,  # LlmAgent requires Pydantic BaseModel
    instruction=(
        "You are an expert resume evaluation specialist.\n"
        "You MUST respond with structured JSON data matching the exact schema. No markdown, no explanations — JSON only.\n\n"

        "=== ANALYSIS REQUIREMENTS ===\n"
        "1. EXECUTIVE SUMMARY — 2-3 sentences covering overall quality and job fit.\n"
        "2. OVERALL SCORE — Rate 1-10 based on quality and job alignment.\n"
        "3. JOB MATCH PERCENTAGE — Precise 0-100 match with job requirements. Use the provided match_percentage from skills analysis.\n"
        "4. SECTION ANALYSIS — Score each section 1-10 with specific, actionable feedback:\n"
        "   - contact_info: professional completeness and presentation\n"
        "   - work_experience: depth, achievements, quantifiable results, STAR format usage\n"
        "   - education: relevance, recency, completeness\n"
        "   - skills: technical breadth and alignment with JD\n"
        "5. STRENGTHS — 3-5 specific resume strengths as strings.\n"
        "6. WEAKNESSES — 3-5 specific areas needing improvement as strings.\n"
        "7. MISSING SKILLS — Be thorough and exhaustive. List every skill, tool, framework, or methodology\n"
        "   that appears in the job description but is absent from the resume. This list is critical —\n"
        "   it drives downstream bullet rewriting, so do not omit minor skills.\n"
        "8. MATCHING SKILLS — Skills that align between resume and JD.\n"
        "9. ATS COMPATIBILITY — Score 1-10 plus:\n"
        "   - issues: specific problems (e.g. missing keywords, table usage, graphics, non-standard section headers,\n"
        "     missing job title keywords, acronyms not spelled out)\n"
        "   - recommendations: concrete fixes for each issue\n\n"

        "=== SECTION CONTENT GUIDELINES ===\n"
        "- EDUCATION: Include major(s), minor(s), clusters, study abroad. First/second year students may include high school.\n"
        "- EXPERIENCE: Include internships, research, part-time, summer, and volunteer work.\n"
        "  Write without 'I' or 'we'. Start with active past-tense verbs.\n"
        "  Evaluate for STAR format (Situation-Task-Action-Result) with measurable outcomes.\n"
        "- ACTIVITIES & LEADERSHIP: Student orgs, extracurricular leadership roles demonstrating career competencies.\n"
        "- SKILLS: Technical, software, lab skills, languages. Keep assessment brief.\n"
        "- PROFESSIONAL SUMMARY: Do NOT recommend adding one.\n\n"

        "=== STAR FORMAT EVALUATION ===\n"
        "For each experience bullet, assess:\n"
        "- Situation: is context provided?\n"
        "- Task: is the specific responsibility clear?\n"
        "- Action: is there a strong active verb and technical detail?\n"
        "- Result: is there a quantified, measurable outcome?\n"
        "Flag bullets missing Result or Action elements as high-priority weaknesses.\n\n"

        "=== SKILLS ANALYSIS INTEGRATION ===\n"
        "When skills analysis data is provided in the prompt:\n"
        "- Use the provided match_percentage for job_match_percentage\n"
        "- Use the provided missing_skills list as a starting point, then expand it\n"
        "- Use the provided matching_skills list\n"
        "- Reference quantified insights in section feedback\n\n"

        "OUTPUT FORMAT: Return ONLY valid JSON matching the schema. No markdown, no code blocks, no explanation."
    ),
    description="Specializes in comprehensive resume evaluation and job matching analysis.",
    tools=[],  # Must be empty when using output_schema
)

# Experience comparison schema for smart replacement
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

# Third agent: Smart Experience Replacement Agent
experience_optimizer_agent = LlmAgent(
    name="experience_optimizer_agent",
    model=os.getenv("REASONING_MODEL", "gemini-2.5-flash"),
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=8000,
        temperature=0.0,
    ),
    output_schema=SmartExperienceOptimization,
    instruction=(
        "You are an expert at optimizing resumes by strategically replacing experiences to improve job alignment.\n\n"

        "=== TASK ===\n"
        "Compare ALL pool experiences against ALL resume experiences to find optimal 1-for-1 replacements.\n\n"

        "=== SCORING CRITERIA (0-100 for each experience) ===\n"
        "Score every resume experience AND every pool experience on:\n"
        "- RELEVANCE TO JOB: how well it matches the job description requirements\n"
        "- SKILL ALIGNMENT: how many required skills it demonstrates\n"
        "- IMPACT: strength of achievements and measurable results\n"
        "Combine these into a single relevance score per experience.\n\n"

        "=== COMPARISON PROCESS ===\n"
        "1. Score ALL resume experiences (0-100).\n"
        "2. Score ALL pool experiences (0-100).\n"
        "3. For each resume experience, find the highest-scoring pool experience that could replace it.\n"
        "4. Recommend replacement ONLY if the pool score exceeds the resume score by 20+ points.\n"
        "5. Each pool experience can replace at most ONE resume experience.\n"
        "6. If two pool experiences are tied for replacing the same resume experience,\n"
        "   choose the one with the larger score difference.\n"
        "7. Never add or remove experiences — only swap 1-for-1.\n\n"

        "=== OUTPUT FORMAT ===\n"
        "For every resume experience provide:\n"
        "- resume_experience_index: index in original resume (0-based)\n"
        "- resume_experience_title: exact title from resume\n"
        "- should_replace: true only if a pool experience scores 20+ points higher\n"
        "- pool_experience_index: index of the replacing pool experience (null if should_replace is false)\n"
        "- relevance_score_resume: score of the original resume experience\n"
        "- relevance_score_pool: score of the best candidate pool experience (0 if none)\n"
        "- replacement_reason: specific explanation of why this swap improves job alignment,\n"
        "  referencing which JD requirements are better addressed\n\n"

        "Be conservative. A swap should only happen when the improvement is clear and meaningful.\n\n"

        "OUTPUT FORMAT: Return ONLY valid JSON matching the schema. No markdown, no explanations."
    ),
    description="Intelligently swaps resume experiences with pool experiences when beneficial for job alignment.",
    tools=[],
)

# Second agent: Resume Rating and Generation Agent
rating_agent = LlmAgent(
    name="resume_rating_and_generation_agent",
    model=os.getenv("REASONING_MODEL", "gemini-2.5-flash"),
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=12000,  # Increased token limit for generating full resumes  
        temperature=0.0,         # Optional: control randomness
    ),
    output_schema=RatingResponse,  # LlmAgent requires Pydantic BaseModel
    instruction=(
        "You are an expert resume content specialist.\n"
        "Your job is to rate resume quality and produce targeted bullet rewrites that improve job alignment.\n\n"

        "=== CRITICAL: EXACT LINE EXTRACTION ===\n"
        "For paraphrasing_suggestion.current_text, you MUST:\n"
        "1. Find the bullet or sentence in the ORIGINAL RESUME TEXT section of the prompt.\n"
        "2. Copy it CHARACTER-BY-CHARACTER — every space, hyphen, period, capitalization, even typos.\n"
        "3. Do NOT paraphrase, improve, or fix it — copy the ACTUAL text.\n"
        "4. Include only ONE complete bullet or sentence, not multiple lines.\n"
        "5. This is used for find-and-replace in the frontend — one wrong character breaks it.\n\n"

        "=== ANTI-HALLUCINATION RULES ===\n"
        "These rules are absolute. Violating them makes the tool harmful:\n"
        "- Do NOT invent metrics, percentages, or numbers the user never mentioned.\n"
        "- Do NOT add technologies, tools, or frameworks the user has not demonstrated.\n"
        "- Only integrate missing skills that PLAUSIBLY relate to what the user actually described.\n"
        "- If a missing skill does not fit the experience, do not force it in.\n"
        "- Rewrites must be grounded in the user's real experience — expanded and sharpened, not fabricated.\n\n"

        "=== SECTION 1: DETAILED RATINGS ===\n"
        "Provide scores 1-10 with detailed justification for:\n"
        "- content_quality: clarity, impact, professionalism of experience descriptions\n"
        "- ats_compatibility: keyword presence, standard headers, no graphics/tables, acronyms spelled out\n"
        "- skills_match: match percentage, list matching and missing skills explicitly\n"
        "- experience_relevance: how well experiences align with JD requirements\n\n"

        "=== SECTION 2: PRIORITY RECOMMENDATIONS (up to 7) ===\n"
        "The prompt provides PRE-SELECTED WEAK BULLETS with RAG templates — rewrite those.\n\n"

        "For EACH recommendation provide:\n"
        "- priority: High / Medium / Low\n"
        "- title: EXACT job title or position name from the resume (helps user identify which experience)\n"
        "- description: what to improve and which missing skills to integrate, and why it matters\n"
        "- specific_example: one-sentence guidance on the improvement approach\n"
        "- paraphrasing_suggestion (REQUIRED for all experience recommendations):\n"
        "  * current_text: one complete line copied EXACTLY from the resume (character-by-character)\n"
        "  * suggested_text: rewritten version that:\n"
        "      - starts with a strong past-tense action verb (no pronouns, no full sentences)\n"
        "      - follows STAR format: [action verb] + [technical approach] + [quantified result]\n"
        "      - naturally integrates 1-2 missing skills that genuinely fit this experience\n"
        "      - adds technical specificity using JD terminology\n"
        "      - stays 20-35 words, uses fragments not sentences\n"
        "      - DOES NOT invent metrics or tools the user has not mentioned\n"
        "  * job_requirement_reference: specific JD requirement this addresses\n"
        "  * alignment_reason: explain (1) which missing skills were added, (2) how STAR format was applied,\n"
        "    (3) why this is grounded in the user's actual experience\n\n"

        "Do NOT recommend adding a professional summary section.\n"
        "Set improved_resume to null — the frontend applies recommendations to the original.\n\n"

        "OUTPUT FORMAT: Return ONLY valid JSON matching RatingResponse schema. No markdown, no code blocks."
    ),
    description="Specializes in resume rating, recommendations, and generating improved versions.",
    tools=[],  # Must be empty when using output_schema
)