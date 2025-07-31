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
    professional_summary: SectionAnalysisItem
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

class ImprovedResume(BaseModel):
    contact_info: str
    professional_summary: str
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
                "professional_summary": {"type": "object", "properties": {"score": {"type": "number"}, "feedback": {"type": "string"}}},
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
                "professional_summary": {"type": "string"},
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
        "   - professional_summary: Effectiveness and job relevance"
        "   - work_experience: Depth, achievements, quantifiable results"
        "   - education: Relevance and presentation"
        "   - skills: Technical and soft skills assessment"
        "5. STRENGTHS - List 3-5 key resume strengths as strings"
        "6. WEAKNESSES - List 3-5 areas needing improvement as strings"
        "7. MISSING SKILLS - Skills required by job but absent from resume"
        "8. MATCHING SKILLS - Skills that align with job requirements"
        "9. ATS COMPATIBILITY - Score, issues list, and recommendations list"
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
        "You are an expert resume rating and improvement specialist. You MUST respond with structured JSON data matching the exact schema provided."
        ""
        "REQUIRED STRUCTURED OUTPUT:"
        "1. DETAILED RATINGS - For each category (1-10 scale):"
        "   - content_quality: score, justification, specific_issues array"
        "   - ats_compatibility: score, justification, missing_keywords array, formatting_issues array"
        "   - skills_match: score, match_percentage, matching_skills array, missing_skills array"
        "   - experience_relevance: score, justification, gaps array"
        ""
        "2. PRIORITY RECOMMENDATIONS - Array of up to 5 recommendations:"
        "   - priority: 'High', 'Medium', or 'Low'"
        "   - title: Brief recommendation title"
        "   - description: Detailed explanation"
        "   - specific_example: Exact text changes or additions"
        ""
        "3. IMPROVED RESUME - Complete structured resume:"
        "   - contact_info: Full contact section as string"
        "   - professional_summary: Enhanced summary as string"
        "   - work_experience: Array of improved job descriptions"
        "   - education: Education section as string"
        "   - skills: Array of skill items"
        "   - additional_sections: Array of other sections (certifications, etc.)"
        ""
        "SKILLS ANALYSIS INTEGRATION:"
        "When skills analysis data is provided:"
        "- Use exact match_percentage for skills_match score calculation"
        "- Include matching_skills in the matching_skills array"
        "- Include missing_skills in the missing_skills array"
        "- Reference specific skills data in justifications"
        ""
        "RESUME IMPROVEMENT RULES:"
        "- Keep all original contact info and factual details"
        "- Enhance content to highlight matching_skills"
        "- Naturally integrate missing_skills into descriptions"
        "- DO NOT add fake experience or positions"
        "- Focus on quantifiable achievements and metrics"
        ""
        "OUTPUT FORMAT: Return ONLY valid JSON matching the schema - no markdown, no explanations."
    ),
    description="Specializes in resume rating, recommendations, and generating improved versions.",
    tools=[],  # Must be empty when using output_schema
)

