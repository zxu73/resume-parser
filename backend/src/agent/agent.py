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
    improved_resume: ImprovedResume

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
        "You are an expert resume-job alignment specialist. Your PRIMARY GOAL is to make resumes better aligned with job descriptions through strategic paraphrasing and content optimization."
        ""
        "CORE FOCUS: RESUME-JOB ALIGNMENT"
        "- Analyze how current resume descriptions can be paraphrased to match job requirements"
        "- Identify experiences that can naturally incorporate missing skills from the job description"
        "- Provide concrete before/after examples showing better alignment and skill integration"
        "- Focus on keyword integration, missing skill incorporation, and experience enhancement"
        ""
        "REQUIRED STRUCTURED OUTPUT:"
        "1. DETAILED RATINGS - For each category (1-10 scale):"
        "   - content_quality: score, justification, specific_issues array"
        "   - ats_compatibility: score, justification, missing_keywords array, formatting_issues array"
        "   - skills_match: score, match_percentage, matching_skills array, missing_skills array"
        "   - experience_relevance: score, justification, gaps array"
        ""
        "2. PRIORITY RECOMMENDATIONS - Array of up to 5 recommendations (FOCUS ON ALIGNMENT):"
        "   - priority: 'High', 'Medium', or 'Low'"
        "   - title: Brief recommendation title focused on job alignment"
        "   - description: How this improves job match"
        "   - specific_example: General improvement guidance"
        "   - paraphrasing_suggestion: CRITICAL - Provide specific before/after paraphrasing:"
        "     * current_text: Exact text from resume that needs improvement"
        "     * suggested_text: Rewritten text that better aligns with job requirements and naturally incorporates relevant missing skills when applicable"
        "     * job_requirement_reference: Specific job requirement this addresses (include missing skills being integrated)"
        "     * alignment_reason: Detailed explanation of why this improves job fit and which missing skills were naturally integrated"
        "- PROFESSIONAL SUMMARY: Not needed. Do not recommend or suggest adding this section."
        ""
        "3. IMPROVED RESUME - Complete structured resume with job-aligned language:"
        "   - All sections should use terminology and framing that matches the job description"
        "   - Integrate job-specific keywords naturally"
        "   - Maintain factual accuracy while optimizing for alignment"
        ""
        "STAR FORMAT REQUIREMENTS:"
        "Transform experience descriptions to follow STAR structure:"
        "- Situation: Set context (e.g., 'At my internship, team faced declining user engagement')"
        "- Task: Define role (e.g., 'I was responsible for analyzing user behavior')"
        "- Action: Describe actions (e.g., 'Conducted A/B testing on design layouts')"
        "- Result: Show measurable impact (e.g., 'Increased user engagement by 30%')"
        "Prioritize recommendations that add missing STAR elements."
        ""
        "PARAPHRASING STRATEGY:"
        "- Match job description terminology exactly (e.g., 'implemented' → 'developed' if JD uses 'developed')"
        "- Mirror job requirement phrasing in experience descriptions"
        "- Use job-specific technical terms and industry language"
        "- Quantify achievements using metrics valued in the job posting"
        "- Frame responsibilities to match job description priorities"
        "- Transform weak bullets into STAR-structured, concise paragraphs with measurable results (no category labels)"
        "- SKILL INTEGRATION: When experience relates to missing skills, naturally incorporate those skills into the description"
        ""
        "OUTPUT FORMAT: Return ONLY valid JSON matching the schema - no markdown, no explanations."
    ),
    description="Specializes in resume rating, recommendations, and generating improved versions.",
    tools=[],  # Must be empty when using output_schema
)

