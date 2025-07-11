import os
import json
import tempfile
import base64
from typing import Any, Dict, List, Optional
from google.genai import types
from google.genai.client import Client
import re

# Initialize Gemini client
client = Client(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_resume_file(file_content: bytes, file_type: str = "pdf") -> Dict[str, Any]:
    """
    Analyze resume file - for now, works best with text files
    
    Args:
        file_content: Raw bytes of the resume file
        file_type: Type of file (pdf, doc, txt)
    
    Returns:
        Dict containing resume analysis results
    """
    try:
        # For text files, extract content directly
        if file_type.lower() == "txt":
            try:
                resume_text = file_content.decode('utf-8')
            except:
                resume_text = file_content.decode('utf-8', errors='ignore')
        else:
            # For PDF/DOC files, for now we'll return a helpful message
            # In production, you'd use a PDF parser like PyPDF2 or similar
            return {
                "error": f"PDF/DOC file upload not yet implemented. Please use text files (.txt) for now, or paste the resume content in the job description field.",
                "success": False,
                "suggestion": "Copy and paste your resume text when using the optimize-resume endpoint."
            }
        
        # Analyze the resume using Gemini
        prompt = f"""
        Please analyze this resume and extract the following information:
        
        RESUME CONTENT:
        {resume_text}
        
        Please provide a structured analysis with:
        
        1. Contact Information (name, email, phone, location)
        2. Professional Summary/Objective
        3. Work Experience (companies, positions, dates, responsibilities)
        4. Education (degrees, institutions, dates)
        5. Skills (technical and soft skills)
        6. Certifications and Awards
        7. Projects (if any)
        8. Overall formatting and ATS compatibility assessment
        
        Please provide analysis that highlights:
        - Key strengths
        - Areas for improvement
        - Missing sections that are commonly expected
        - ATS optimization suggestions
        
        Format your response as a detailed analysis with clear sections.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        
        return {
            "analysis": response.text,
            "file_type": file_type,
            "success": True
        }
        
    except Exception as e:
        return {"error": f"Resume analysis failed: {str(e)}", "success": False}

def analyze_job_description(job_description: str) -> Dict[str, Any]:
    """
    Analyze job description to extract requirements and skills using Gemini AI
    
    Args:
        job_description: The job description text
    
    Returns:
        Dict containing job analysis results
    """
    try:
        # Use Gemini AI to extract comprehensive information from job description
        prompt = f"""
        Please analyze this job description and extract the following information:

        JOB DESCRIPTION:
        {job_description}

        Please extract and categorize:

        1. **Technical Skills** (programming languages, frameworks, tools, technologies):
           - List all mentioned technical skills
           - Include variations (e.g., React, React.js, ReactJS)
           - Don't miss domain-specific tools

        2. **Soft Skills** (communication, leadership, problem-solving, etc.):
           - List all mentioned soft skills and interpersonal abilities

        3. **Experience Requirements**:
           - Years of experience required (extract exact numbers)
           - Specific experience types (e.g., "3+ years Python", "2 years team lead")

        4. **Education Requirements**:
           - Degree requirements (Bachelor's, Master's, PhD)
           - Specific fields of study
           - Certifications mentioned

        5. **Job Level** (entry, mid, senior, lead, principal, etc.)

        6. **Industry/Domain** (healthcare, fintech, e-commerce, etc.)

        7. **Required vs Preferred** qualifications (separate these clearly)

        8. **Company Culture/Values** indicators

        Provide your response in this exact JSON format:
        {{
            "technical_skills": ["skill1", "skill2", "..."],
            "soft_skills": ["skill1", "skill2", "..."],
            "experience_years": "X+ years" or "X-Y years" or "Not specified",
            "specific_experience": ["experience1", "experience2", "..."],
            "education_required": true/false,
            "education_details": "description of education requirements",
            "certifications": ["cert1", "cert2", "..."],
            "job_level": "entry/mid/senior/lead/principal/executive",
            "industry": "industry name",
            "required_qualifications": ["req1", "req2", "..."],
            "preferred_qualifications": ["pref1", "pref2", "..."],
            "company_culture": "brief description",
            "all_skills": ["combined list of all skills"]
        }}
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        
        # Parse the JSON response from Gemini
        import json
        try:
            # Extract JSON from the response (in case there's extra text)
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]  # Remove ```json and ```
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]  # Remove ``` and ```
            
            ai_analysis = json.loads(response_text)
            
            # Combine technical and soft skills for backward compatibility
            all_skills = ai_analysis.get("all_skills", [])
            if not all_skills:
                all_skills = ai_analysis.get("technical_skills", []) + ai_analysis.get("soft_skills", [])
            
            return {
                "skills_required": all_skills,  # For backward compatibility
                "technical_skills": ai_analysis.get("technical_skills", []),
                "soft_skills": ai_analysis.get("soft_skills", []),
                "experience_years": ai_analysis.get("experience_years", "Not specified"),
                "specific_experience": ai_analysis.get("specific_experience", []),
                "education_required": ai_analysis.get("education_required", False),
                "education_details": ai_analysis.get("education_details", ""),
                "certifications": ai_analysis.get("certifications", []),
                "job_level": ai_analysis.get("job_level", "mid"),
                "industry": ai_analysis.get("industry", "Not specified"),
                "required_qualifications": ai_analysis.get("required_qualifications", []),
                "preferred_qualifications": ai_analysis.get("preferred_qualifications", []),
                "company_culture": ai_analysis.get("company_culture", ""),
                "raw_text": job_description,
                "analysis_summary": f"Found {len(all_skills)} skills, {ai_analysis.get('experience_years', 'Not specified')} experience, {ai_analysis.get('job_level', 'mid')} level",
                "success": True
            }
            
        except json.JSONDecodeError:
            # Fallback: if JSON parsing fails, return the raw analysis
            return {
                "raw_analysis": response.text,
                "skills_required": [],  # Empty for backward compatibility
                "experience_years": "Not specified",
                "education_required": False,
                "job_level": "mid",
                "raw_text": job_description,
                "analysis_summary": "AI analysis completed (JSON parsing failed)",
                "success": True,
                "note": "Full analysis available in raw_analysis field"
            }
        
    except Exception as e:
        return {"error": f"Job description analysis failed: {str(e)}", "success": False}

def compare_resume_to_job(resume_analysis: Dict[str, Any], job_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare resume against job requirements and provide optimization suggestions
    
    Args:
        resume_analysis: Results from resume analysis
        job_analysis: Results from job description analysis
    
    Returns:
        Dict containing comparison results and suggestions
    """
    try:
        if not resume_analysis.get("success") or not job_analysis.get("success"):
            return {"error": "Invalid input data", "success": False}
        
        # Use Gemini to perform detailed comparison
        prompt = f"""
        Please compare this resume analysis with the job requirements and provide detailed optimization suggestions:

        RESUME ANALYSIS:
        {resume_analysis.get('analysis', '')}

        JOB REQUIREMENTS:
        Required Skills: {', '.join(job_analysis.get('skills_required', []))}
        Experience: {job_analysis.get('experience_years', 'Not specified')}
        Education: {'Required' if job_analysis.get('education_required') else 'Not specified'}
        Job Level: {job_analysis.get('job_level', 'Not specified')}

        JOB DESCRIPTION:
        {job_analysis.get('raw_text', '')}

        Please provide:
        1. Match Score (0-100%): How well does the resume match the job requirements?
        2. Strengths: What aspects of the resume align well with the job?
        3. Gaps: What's missing from the resume that the job requires?
        4. Specific Recommendations: Concrete suggestions for improving the resume
        5. ATS Optimization: Tips for improving ATS compatibility
        6. Keywords to Add: Specific keywords that should be incorporated
        7. Industry Insights: Brief insights about this role/industry

        Be specific and actionable in your recommendations.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        
        return {
            "comparison_analysis": response.text,
            "job_skills": job_analysis.get('skills_required', []),
            "job_level": job_analysis.get('job_level', 'Not specified'),
            "experience_requirement": job_analysis.get('experience_years', 'Not specified'),
            "success": True
        }
        
    except Exception as e:
        return {"error": f"Comparison failed: {str(e)}", "success": False}
