#!/usr/bin/env python3
"""
Simple skills analysis function for resume agents
"""

import json
import os
import re
from typing import Dict, Any, List
from google.genai import types
from google.genai.client import Client

# Initialize Gemini client
client = Client(api_key=os.getenv("GEMINI_API_KEY"))

def extract_skills_from_text(text: str, context: str) -> List[str]:
    """
    Extract skills from text using AI when JSON parsing fails
    
    Args:
        text: The text to extract skills from
        context: Context about what type of skills to extract
        
    Returns:
        List of extracted skills
    """
    try:
        prompt = f"""
        Extract skills from this {context}:
        
        {text}
        
        Return only a comma-separated list of skills (no explanations):
        Example: python, javascript, aws, docker, project management
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        
        # Parse comma-separated skills
        skills_text = response.text.strip()
        skills = [skill.strip() for skill in skills_text.split(',') if skill.strip()]
        return skills
        
    except Exception:
        return []

def calculate_match_percentage(matching_skills: List[str], job_skills: List[str]) -> int:
    """Calculate match percentage between skills"""
    if not job_skills:
        return 0
    return int((len(matching_skills) / len(job_skills)) * 100)

def analyze_skills_matching(resume_text: str, job_description: str) -> Dict[str, Any]:
    """
    Analyze skills matching between resume and job description using AI
    
    Args:
        resume_text: The resume content
        job_description: The job description content
        
    Returns:
        Dict with skills analysis results
    """
    try:
        prompt = f"""
        Extract and compare skills from these two texts:

        RESUME:
        {resume_text}

        JOB DESCRIPTION:
        {job_description}

        Return JSON with:
        {{
            "resume_skills": ["skill1", "skill2"],
            "job_skills": ["skill1", "skill2"],
            "matching_skills": ["skill1"],
            "missing_skills": ["skill2"],
            "match_percentage": 75,
            "summary": "Brief analysis"
        }}

        Extract technical skills, tools, frameworks, and relevant soft skills.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        
        # Try to parse JSON response
        response_text = response.text.strip()
        
        # Extract JSON from markdown code blocks
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end]
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end]
        
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            # Dynamic fallback: extract skills separately
            resume_skills = extract_skills_from_text(resume_text, "resume")
            job_skills = extract_skills_from_text(job_description, "job description")
            
            # Find matching skills dynamically
            matching_skills = [skill for skill in resume_skills if skill.lower() in [js.lower() for js in job_skills]]
            missing_skills = [skill for skill in job_skills if skill.lower() not in [rs.lower() for rs in resume_skills]]
            
            # Calculate dynamic match percentage
            match_percentage = calculate_match_percentage(matching_skills, job_skills)
            
            return {
                "resume_skills": resume_skills,
                "job_skills": job_skills,
                "matching_skills": matching_skills,
                "missing_skills": missing_skills,
                "match_percentage": match_percentage,
                "summary": f"Skills analysis completed via fallback method. Found {len(matching_skills)} matching skills out of {len(job_skills)} required skills.",
                "fallback_used": True
            }
            
    except Exception as e:
        return {
            "resume_skills": [],
            "job_skills": [],
            "matching_skills": [],
            "missing_skills": [],
            "match_percentage": 0,
            "summary": f"Skills analysis failed: {str(e)}",
            "error": str(e)
        } 