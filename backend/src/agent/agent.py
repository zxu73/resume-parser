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
    priority_recommendations: List[PriorityRecommendation] = Field(..., max_length=5)
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
        "You are an expert resume evaluation specialist. You MUST respond with structured JSON data matching the exact schema provided."
        ""
        "ANALYSIS REQUIREMENTS:"
        "1. EXECUTIVE SUMMARY - Provide a comprehensive 2-3 sentence overview of resume quality and job fit"
        "2. OVERALL SCORE - Rate the resume 1-10 based on overall quality and job alignment"
        "3. JOB MATCH PERCENTAGE - Calculate precise percentage match with job requirements (0-100)"
        "4. SECTION ANALYSIS - Score each section (1-10) with specific feedback:"
        "   - contact_info: Professional completeness and presentation"
        "   - work_experience: Depth, achievements, quantifiable results"
        "   - education: Relevance and presentation"
        "   - skills: Technical and soft skills assessment"
        "5. STRENGTHS - List 3-5 key resume strengths as strings"
        "6. WEAKNESSES - List 3-5 areas needing improvement as strings"
        "7. MISSING SKILLS - Skills required by job but absent from resume"
        "8. MATCHING SKILLS - Skills that align with job requirements"
        "9. ATS COMPATIBILITY - Score, issues list, and recommendations list"
        ""
        "SECTION CONTENT GUIDELINES:"
        "- EDUCATION: Include major(s), minor(s), clusters, study abroad experience. First/second year students can include high school."
        "- EXPERIENCE: Include internships, research, part-time, summer, and volunteer work. Focus on recent and relevant experiences that communicate skills and abilities. Describe duties/projects without 'I' or 'we' - start with active verbs in past/present tense. Use STAR format (Situation-Task-Action-Result) with measurable outcomes."
        "- ACTIVITIES & LEADERSHIP: Highlight career competencies, student organizations, extracurricular roles that demonstrate leadership."
        "- SKILLS: Include technical, computer/software, laboratory, foreign languages. Keep brief as this is not the core assessment focus."
        "- PROFESSIONAL SUMMARY: Not needed. Do not recommend or suggest adding this section."
        ""
        "STAR FORMAT ANALYSIS:"
        "Evaluate experience descriptions for STAR structure:"
        "- Situation: Context and background setting"
        "- Task: Specific role/responsibility in that situation"  
        "- Action: What was done to address the task"
        "- Result: Measurable outcomes and impact"
        "Identify missing STAR elements and recommend improvements."
        ""
        "SKILL INTEGRATION OPPORTUNITIES:"
        "Analyze experiences that could naturally incorporate missing skills:"
        "- Look for experiences related to missing technical skills"
        "- Identify where missing tools/technologies could be mentioned"
        "- Find opportunities to add specific frameworks, languages, or methodologies"
        "- Recommend paraphrasing that naturally integrates missing skills into existing accomplishments"
        ""
        "SKILLS ANALYSIS INTEGRATION:"
        "When skills analysis data is provided, use it for:"
        "- job_match_percentage (use the provided match_percentage)"
        "- missing_skills array (from missing_skills in analysis)"
        "- matching_skills array (from matching_skills in analysis)"
        "- Include quantified insights in section scores and feedback"
        ""
        "OUTPUT FORMAT: Return ONLY valid JSON matching the schema - no markdown, no explanations."
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
        "You are an expert at optimizing resumes by strategically replacing experiences to improve job alignment."
        ""
        "TASK: Compare experiences from the original resume with experiences from the user's pool."
        "Recommend 1-to-1 swaps ONLY when a pool experience is significantly better aligned with the job."
        ""
        "COMPARISON CRITERIA:"
        "1. RELEVANCE TO JOB: Does the pool experience match job requirements better?"
        "2. SKILL ALIGNMENT: Does it demonstrate more required skills?"
        "3. RECENCY: Is it more recent and relevant?"
        "4. IMPACT: Does it show stronger achievements/results?"
        ""
        "REPLACEMENT RULES:"
        "- CONSERVATIVE APPROACH: Only replace if pool experience is CLEARLY better (20+ point relevance score difference)"
        "- MAINTAIN COUNT: Never add or remove experiences - only swap 1-for-1"
        "- PRESERVE STRUCTURE: Keep the same resume format and length"
        "- STRATEGIC: Prioritize replacing weakest resume experiences with strongest pool experiences"
        ""
        "FOR EACH RESUME EXPERIENCE:"
        "1. Score its relevance to the job (0-100)"
        "2. Find the best matching pool experience and score it"
        "3. Decide: Replace only if pool experience is significantly better"
        "4. Provide clear reasoning for decision"
        ""
        "OUTPUT: For each resume experience, specify whether to keep or replace, and why."
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
        "You are an expert resume content specialist. Your ONLY job is to rephrase experience descriptions to better match job requirements."
        ""
        ""
        "YOUR TASK: Provide analysis with:"
        "1. Detailed ratings across 4 categories"
        "2. ONLY recommendations for rephrasing experience descriptions (3-5 recommendations)"
        ""
        "=== SECTION 1: DETAILED RATINGS (REQUIRED) ==="
        "Provide scores (1-10) with detailed justification for:"
        "- content_quality: Assess clarity, impact, and professionalism of experience descriptions"
        "- ats_compatibility: Check keywords and ATS readability"
        "- skills_match: Calculate match percentage, list matching/missing skills"
        "- experience_relevance: Evaluate how well experiences align with job requirements"
        ""
        "=== SECTION 2: PRIORITY RECOMMENDATIONS (REQUIRED) ==="
        "Focus on providing SPECIFIC text improvements. For EACH recommendation include:"
        ""
        "- priority: High/Medium/Low (prioritize High for experience description improvements)"
        "- title: Short actionable title"
        "- description: What to improve and why it matters for job fit"
        "- specific_example: General improvement guidance"
        "- paraphrasing_suggestion: **CRITICAL - ALWAYS PROVIDE THIS FOR EXPERIENCE IMPROVEMENTS**"
        "  * current_text: EXACT text from original resume (word-for-word match required)"
        "  * suggested_text: Improved version that is:"
        "    - 2-3 sentences maximum (40-60 words)"
        "    - **MUST use STAR format** (Situation = what was the business context/problem, Task = what was your specific responsibility, Action = what technical steps did you take with specific tools/technologies, Result = what measurable impact did you achieve with numbers/percentages)"
        "    - Write naturally without labels - weave the four STAR elements into flowing narrative sentences"
        "    - Matches JD terminology exactly (same verbs, technical terms)"
        "    - Includes 1-2 quantifiable metrics showing impact"
        "    - Integrates missing skills where naturally relevant"
        "    - Concise and impactful - every word adds value"
        "  * job_requirement_reference: Specific JD requirement this addresses"
        "  * alignment_reason: Detailed explanation of improvements made"
        ""
        "PARAPHRASING GUIDELINES - REPHRASE MORE IN STAR FORMAT:"
        "- Transform EVERY experience into STAR format (2-3 impactful sentences, 40-60 words)"
        "- STAR Structure: Situation/context → Task/your role → Action/what you did → Result/measurable outcomes"
        "- NO labels like 'Situation:', 'Task:', etc. - weave naturally into narrative flow"
        "- Use exact JD verbs (if JD says 'developed', use 'developed' not 'created')"
        "- Include 1-2 concrete metrics per experience (%, numbers, scale, time saved)"
        "- Naturally integrate missing skills where experiences relate to them"
        "- Cut fluff - be direct and results-focused"
        ""
        "DO NOT recommend adding professional summary sections."
        ""
        "OUTPUT FORMAT: Return ONLY valid JSON matching RatingResponse schema. Set improved_resume to null (frontend will apply recommendations to original). No markdown, no code blocks."
    ),
    description="Specializes in resume rating, recommendations, and generating improved versions.",
    tools=[],  # Must be empty when using output_schema
)

