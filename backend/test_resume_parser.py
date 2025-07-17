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

def test_direct_resume_evaluation():
    """Test the direct resume evaluation endpoint with resume text and job description"""
    print("\n🎯 Testing Direct Resume Evaluation (Sequential Agent Workflow)...")
    
    sample_resume_text = """
    John Doe
    Senior Software Engineer
    Email: john.doe@email.com
    Phone: (555) 123-4567
    Location: San Francisco, CA
    
    PROFESSIONAL SUMMARY
    Experienced software engineer with 4 years of experience in full-stack development.
    Skilled in Python, React, and cloud technologies. Proven track record of delivering
    scalable web applications and leading development teams.
    
    WORK EXPERIENCE
    
    Senior Software Engineer | Tech Company | Jan 2020 - Present
    • Developed and maintained web applications using Python, Django, and React
    • Worked with AWS services including EC2, S3, and RDS
    • Collaborated with cross-functional teams using Agile/Scrum methodology
    • Implemented CI/CD pipelines using Docker and Jenkins
    • Mentored 2 junior developers and conducted code reviews
    • Improved application performance by 30% through optimization
    
    Junior Software Developer | Startup Inc | Jun 2019 - Dec 2019
    • Built responsive frontend components using React and TypeScript
    • Participated in daily standups and sprint planning
    • Wrote unit tests and integration tests
    • Assisted in database design and optimization
    
    EDUCATION
    Bachelor of Science in Computer Science | University of California | 2019
    GPA: 3.7/4.0
    Relevant Coursework: Data Structures, Algorithms, Database Systems, Software Engineering
    
    TECHNICAL SKILLS
    • Programming Languages: Python, JavaScript, TypeScript, Java, SQL
    • Frontend: React, HTML5, CSS3, Redux, Material-UI
    • Backend: Django, Flask, Node.js, Express.js
    • Databases: PostgreSQL, MySQL, MongoDB
    • Cloud: AWS (EC2, S3, RDS, Lambda), Docker, Kubernetes
    • Tools: Git, Jenkins, JIRA, VS Code, Postman
    
    PROJECTS
    E-commerce Platform (2023)
    • Built a full-stack e-commerce application using React and Django
    • Implemented payment integration with Stripe API
    • Deployed on AWS with auto-scaling capabilities
    
    CERTIFICATIONS
    • AWS Certified Solutions Architect - Associate (2023)
    • Certified Scrum Master (2022)
    """
    
    sample_job_description = """
    Senior Python Developer
    
    We are seeking a Senior Python Developer with 5+ years of experience to join our team.
    
    Required Qualifications:
    • 5+ years of Python programming experience
    • Strong experience with Django or Flask frameworks
    • Frontend development experience with React.js
    • AWS cloud services experience (EC2, S3, RDS)
    • Docker containerization experience
    • SQL database management skills
    • Git version control proficiency
    • Team leadership and mentoring experience
    
    Preferred Qualifications:
    • Machine learning or data science experience
    • Kubernetes orchestration experience
    • Microservices architecture experience
    • DevOps and CI/CD pipeline experience
    • Agile/Scrum methodology experience
    • AWS certifications
    
    Education:
    Bachelor's degree in Computer Science, Engineering, or related field
    
    Responsibilities:
    • Lead development of scalable web applications
    • Architect and implement backend systems
    • Mentor junior developers and conduct code reviews
    • Collaborate with cross-functional teams
    • Design and implement RESTful APIs
    • Optimize application performance and scalability
    • Participate in technical decision-making
    """
    
    payload = {
        "resume_text": sample_resume_text,
        "job_description": sample_job_description
    }
    
    try:
        print("   🔄 Running direct resume evaluation...")
        print("   📝 Resume: 4 years experience, Python/React skills, AWS experience")
        print("   💼 Job: Senior Python Developer, 5+ years required")
        print("   🤖 Comprehensive Agent Workflow:")
        print("      Single agent provides: Evaluation + Rating + Recommendations")
        
        response = requests.post(f"{BASE_URL}/evaluate-resume", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Direct resume evaluation successful!")
            print(f"   Workflow Type: {result.get('workflow_type', 'N/A')}")
            
            # Display comprehensive analysis
            if result.get('comprehensive_analysis'):
                print("\n   📊 COMPREHENSIVE ANALYSIS:")
                print("   " + "="*60)
                print(result['comprehensive_analysis'])
                print("   " + "="*60)
            
            return True
        else:
            print(f"❌ Direct resume evaluation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing direct resume evaluation: {e}")
        return False

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
    
    # Test the main functionality: Direct resume evaluation
    if os.getenv("GEMINI_API_KEY"):
        print("\n🎯 Testing Main Functionality: Direct Resume Evaluation")
        if test_direct_resume_evaluation():
            print("✅ Direct resume evaluation test passed!")
        else:
            print("❌ Direct resume evaluation test failed")
            return
    else:
        print("\n⚠️  Cannot test main functionality - GEMINI_API_KEY not set")
        print("   Please set GEMINI_API_KEY environment variable to test the sequential agent workflow")
        return
    
    # Test additional endpoints
    print("\n🔧 Testing Additional Endpoints...")
    
    # Test job description analysis
    if not test_job_description_analysis():
        print("❌ Job description analysis test failed")
        return
    
    # Test resume upload workflow
    analysis_id = test_resume_upload()
    if analysis_id:
        print("✅ Resume upload test passed!")
        
        # Test other endpoints if API key is available
        if os.getenv("GEMINI_API_KEY"):
            print("\n🤖 Testing Additional AI Workflows...")
            
            # Test resume optimization
            if test_resume_optimization(analysis_id):
                print("✅ Resume optimization test passed!")
            else:
                print("❌ Resume optimization test failed")
    else:
        print("❌ Resume upload test failed")
    
    print("\n✅ All tests completed!")
    print("\n📝 Summary:")
    print("   ✅ Main Feature: Direct resume evaluation with job description")
    print("   ✅ Users can input resume text and job description directly")
    print("   ✅ Comprehensive agent workflow: Evaluation + Rating + Recommendations")
    print("   ✅ No file upload required for main functionality")
    print("\n🚀 To use the main feature:")
    print("   1. Start server: adk web")
    print("   2. POST to /evaluate-resume with:")
    print("      - resume_text: Your resume content")
    print("      - job_description: The job posting")
    print("   3. Get comprehensive evaluation, ratings, and recommendations!")

if __name__ == "__main__":
    main() 