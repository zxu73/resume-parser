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
import PyPDF2
import io
import docx

# Initialize Gemini client
client = Client(api_key=os.getenv("GEMINI_API_KEY"))

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF content"""
    try:
        pdf_file = io.BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX content"""
    try:
        doc_file = io.BytesIO(content)
        doc = docx.Document(doc_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting DOCX text: {str(e)}"

def analyze_resume_file(content: bytes, file_extension: str) -> Dict[str, Any]:
    """
    Analyze a resume file and extract text content
    
    Args:
        content: File content as bytes
        file_extension: File extension (pdf, doc, docx, txt)
        
    Returns:
        Dict with analysis results
    """
    try:
        # Extract text based on file type
        if file_extension.lower() == 'pdf':
            text = extract_text_from_pdf(content)
        elif file_extension.lower() in ['doc', 'docx']:
            text = extract_text_from_docx(content)
        elif file_extension.lower() == 'txt':
            text = content.decode('utf-8')
        else:
            return {
                "success": False,
                "error": f"Unsupported file type: {file_extension}"
            }
        
        if not text or text.startswith("Error"):
            return {
                "success": False,
                "error": f"Failed to extract text from file: {text}"
            }
        
        # Basic analysis using AI
        prompt = f"""
        Analyze this resume and provide a structured summary:

        RESUME TEXT:
        {text}

        Provide a comprehensive analysis covering:
        - Contact information
        - Professional summary/objective
        - Work experience highlights
        - Education
        - Skills and competencies
        - Overall impression and suggestions

        Be thorough and specific in your analysis.
        """
        
        response = client.models.generate_content(
            model=os.getenv("REASONING_MODEL", "gemini-2.5-flash"),
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        
        return {
            "success": True,
            "analysis": response.text,
            "extracted_text": text
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Resume analysis failed: {str(e)}"
        }

def analyze_job_description(job_description: str) -> Dict[str, Any]:
    """
    Analyze a job description to extract requirements and key information
    
    Args:
        job_description: The job description text
        
    Returns:
        Dict with analysis results
    """
    try:
        prompt = f"""
        Analyze this job description and extract key information:

        JOB DESCRIPTION:
        {job_description}

        Provide analysis covering:
        - Job title and level
        - Key responsibilities
        - Required skills and qualifications
        - Preferred qualifications
        - Experience requirements
        - Industry and company context
       

        Be specific about requirements vs preferences.
        """
        
        response = client.models.generate_content(
            model=os.getenv("REASONING_MODEL", "gemini-2.5-flash"),
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        
        return {
            "success": True,
            "analysis": response.text,
            "job_description": job_description
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Job description analysis failed: {str(e)}"
        }

def compare_resume_to_job(resume_analysis: Dict[str, Any], job_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare resume analysis with job description analysis
    
    Args:
        resume_analysis: Resume analysis results
        job_analysis: Job description analysis results
        
    Returns:
        Dict with comparison results
    """
    try:
        prompt = f"""
        Compare this resume with the job requirements and provide optimization suggestions:

        RESUME ANALYSIS:
        {resume_analysis.get('analysis', '')}

        JOB REQUIREMENTS:
        {job_analysis.get('analysis', '')}

        Provide comparison covering:
        - Skills match analysis
        - Experience alignment
        - Missing qualifications
        - Strengths that align with the role
        - Areas for improvement
        - Specific optimization recommendations
        - ATS compatibility suggestions

        Be specific about gaps and matches.
        """
        
        response = client.models.generate_content(
            model=os.getenv("REASONING_MODEL", "gemini-2.5-flash"),
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        
        return {
            "success": True,
            "comparison": response.text,
            "match_analysis": "Detailed comparison completed"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Resume-job comparison failed: {str(e)}"
        }

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
            model=os.getenv("REASONING_MODEL", "gemini-2.5-flash"),
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(max_output_tokens=2000)
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
            model=os.getenv("REASONING_MODEL", "gemini-2.5-flash"),
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(max_output_tokens=4000)
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
            
            # Find matching skills dynamically with flexible matching
            def skills_match(skill1: str, skill2: str) -> bool:
                """Check if two skills match (exact, contains, or share keywords)"""
                s1 = skill1.lower().strip()
                s2 = skill2.lower().strip()
                # Exact match
                if s1 == s2:
                    return True
                # One contains the other (handles "React" vs "React.js")
                if s1 in s2 or s2 in s1:
                    return True
                # Share significant words (handles abbreviations naturally)
                words1 = set(w for w in s1.split() if len(w) > 2)
                words2 = set(w for w in s2.split() if len(w) > 2)
                if words1 and words2 and words1 & words2:
                    return True
                return False
            
            matching_skills = []
            for resume_skill in resume_skills:
                for job_skill in job_skills:
                    if skills_match(resume_skill, job_skill):
                        if resume_skill not in matching_skills:
                            matching_skills.append(resume_skill)
                        break
            
            missing_skills = []
            for job_skill in job_skills:
                if not any(skills_match(resume_skill, job_skill) for resume_skill in resume_skills):
                    missing_skills.append(job_skill)
            
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


def analyze_experience_structure(resume_text: str) -> Dict[str, Any]:
    """
    Analyze the structure and quality of work experience descriptions.
    
    Args:
        resume_text: The resume content
        
    Returns:
        Dict with experience structure analysis
    """
    try:
        prompt = f"""
        Analyze the work experience section structure in this resume:

        RESUME:
        {resume_text}

        Return JSON with:
        {{
            "total_experiences": 3,
            "experiences_with_metrics": 2,
            "experiences_with_action_verbs": 3,
            "average_bullet_length": "medium",
            "star_format_usage": "partial",
            "structure_score": 7,
            "strengths": ["Clear action verbs", "Includes metrics"],
            "weaknesses": ["Some experiences lack results", "Inconsistent formatting"]
        }}

        Evaluate: action verbs, quantifiable results, STAR format, consistency.
        """
        
        response = client.models.generate_content(
            model=os.getenv("REASONING_MODEL", "gemini-2.5-flash"),
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(max_output_tokens=2000)
        )
        
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
            # Fallback
            return {
                "total_experiences": resume_text.count("•") // 3 if "•" in resume_text else 2,
                "structure_score": 6,
                "summary": "Experience structure analysis (fallback mode)",
                "fallback_used": True
            }
            
    except Exception as e:
        return {
            "total_experiences": 0,
            "structure_score": 0,
            "summary": f"Experience analysis failed: {str(e)}",
            "error": str(e)
        }
