#!/usr/bin/env python3
"""
Simple test script for the resume parser endpoints.
Run this script to test the server functionality.
"""

import requests
import json
import tempfile
import os

# Server configuration
BASE_URL = "http://localhost:8000"

def test_server_health():
    """Test if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"✅ Server is running (status: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start the server first with 'adk web'")
        return False

def test_job_description_analysis():
    """Test job description analysis endpoint"""
    print("\n🔍 Testing Job Description Analysis...")
    
    sample_job_description = """
    Senior Software Engineer
    
    We are looking for a Senior Software Engineer with 5+ years of experience.
    
    Required Skills:
    - Python programming
    - React.js frontend development
    - SQL databases
    - AWS cloud services
    - Git version control
    
    Preferred:
    - Docker containerization
    - Machine learning experience
    - Agile/Scrum methodology
    
    Education: Bachelor's degree in Computer Science or related field.
    """
    
    payload = {
        "job_description": sample_job_description
    }
    
    try:
        response = requests.post(f"{BASE_URL}/analyze-job-description", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Job description analysis successful!")
            print(f"   Found skills: {result['analysis']['skills_required']}")
            print(f"   Experience: {result['analysis']['experience_years']}")
            print(f"   Job level: {result['analysis']['job_level']}")
            return True
        else:
            print(f"❌ Job description analysis failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing job description analysis: {e}")
        return False

def create_sample_resume_file():
    """Create a sample text resume file for testing"""
    sample_resume = """
    John Doe
    Software Engineer
    Email: john.doe@email.com
    Phone: (555) 123-4567
    
    PROFESSIONAL SUMMARY
    Experienced software engineer with 4 years of experience in full-stack development.
    
    WORK EXPERIENCE
    Software Engineer | Tech Company | 2020-2024
    - Developed web applications using Python and React
    - Worked with SQL databases and cloud services
    - Collaborated with cross-functional teams using Agile methodology
    
    Junior Developer | Startup Inc | 2019-2020
    - Built frontend components using JavaScript and HTML/CSS
    - Participated in code reviews and testing
    
    EDUCATION
    Bachelor of Science in Computer Science | University Name | 2019
    
    SKILLS
    - Programming Languages: Python, JavaScript, Java
    - Frameworks: React, Django, Flask
    - Databases: MySQL, PostgreSQL
    - Tools: Git, Docker, VS Code
    """
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(sample_resume)
        return f.name

def test_resume_upload():
    """Test resume upload endpoint"""
    print("\n📄 Testing Resume Upload...")
    
    # Create sample resume file
    resume_file_path = create_sample_resume_file()
    
    try:
        with open(resume_file_path, 'rb') as f:
            files = {'file': ('sample_resume.txt', f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/upload-resume", files=files)
        
        # Clean up temporary file
        os.unlink(resume_file_path)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Resume upload successful!")
            print(f"   Analysis ID: {result['analysis_id']}")
            print(f"   Filename: {result['filename']}")
            print("   Full Analysis:")
            print("   " + "="*50)
            print(result['analysis'])
            print("   " + "="*50)
            return result['analysis_id']
        else:
            print(f"❌ Resume upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error testing resume upload: {e}")
        if os.path.exists(resume_file_path):
            os.unlink(resume_file_path)
        return None

def test_resume_optimization(analysis_id):
    """Test resume optimization endpoint"""
    print("\n🚀 Testing Resume Optimization...")
    
    sample_job_description = """
    Senior Python Developer
    
    Requirements:
    - 5+ years Python experience
    - React.js frontend skills
    - AWS cloud experience
    - Docker containerization
    - Machine learning knowledge
    - Team leadership experience
    """
    
    payload = {
        "resume_analysis_id": analysis_id,
        "job_description": sample_job_description
    }
    
    try:
        response = requests.post(f"{BASE_URL}/optimize-resume", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Resume optimization successful!")
            print("   Full Optimization Suggestions:")
            print("   " + "="*50)
            print(result['optimization_suggestions'])
            print("   " + "="*50)
            return True
        else:
            print(f"❌ Resume optimization failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing resume optimization: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Resume Parser API Endpoints")
    print("=" * 50)
    
    # Check if server is running
    if not test_server_health():
        return
    
    # Test job description analysis
    if not test_job_description_analysis():
        print("❌ Job description analysis test failed")
        return
    
    # Test resume upload
    analysis_id = test_resume_upload()
    if not analysis_id:
        print("❌ Resume upload test failed")
        return
    
    # Test resume optimization (requires GEMINI_API_KEY)
    if os.getenv("GEMINI_API_KEY"):
        test_resume_optimization(analysis_id)
    else:
        print("\n⚠️  Skipping resume optimization test (GEMINI_API_KEY not set)")
    
    print("\n✅ All available tests completed!")
    print("\n📝 To fully test the resume parser:")
    print("   1. Make sure you have GEMINI_API_KEY set in your environment")
    print("   2. Start the server with: adk web")
    print("   3. Try uploading a real PDF resume through the API")

if __name__ == "__main__":
    main() 