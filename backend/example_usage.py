#!/usr/bin/env python3
"""
Example usage of the direct resume evaluation endpoint.
This demonstrates the main functionality: input resume text and job description,
get comprehensive evaluation and ratings from sequential agents.
"""

import requests
import json

# Server configuration
BASE_URL = "http://localhost:8000"

def evaluate_resume_example():
    """Example of how to use the direct resume evaluation endpoint"""
    
    # Sample resume text
    resume_text = """
    Jane Smith
    Software Engineer
    Email: jane.smith@email.com
    Phone: (555) 987-6543
    
    PROFESSIONAL SUMMARY
    Software engineer with 3 years of experience in web development.
    
    WORK EXPERIENCE
    Software Engineer | ABC Company | 2021-2024
    • Developed web applications using Python and JavaScript
    • Worked with databases and APIs
    • Collaborated with team members on projects
    
    EDUCATION
    Bachelor of Science in Computer Science | XYZ University | 2021
    
    SKILLS
    • Python, JavaScript, HTML, CSS
    • Django, React
    • Git, SQL
    """
    
    # Sample job description
    job_description = """
    Senior Python Developer
    
    We are looking for a Senior Python Developer with 5+ years of experience.
    
    Required:
    • 5+ years Python experience
    • Django/Flask framework experience
    • React.js frontend skills
    • AWS cloud experience
    • Team leadership experience
    
    Preferred:
    • Machine learning knowledge
    • Docker containerization
    • Microservices architecture
    """
    
    # Prepare the request
    payload = {
        "resume_text": resume_text,
        "job_description": job_description
    }
    
    print("🎯 Resume Evaluation Example")
    print("=" * 50)
    print("📝 Resume: 3 years experience, Python/JavaScript skills")
    print("💼 Job: Senior Python Developer, 5+ years required")
    print("\n🤖 Running Comprehensive Agent Workflow...")
    print("   Single agent provides: Evaluation + Rating + Recommendations")
    
    try:
        # Make the request
        response = requests.post(f"{BASE_URL}/evaluate-resume", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Evaluation completed successfully!")
            
            # Display the comprehensive analysis
            print("\n" + "="*60)
            print("📊 COMPREHENSIVE ANALYSIS")
            print("="*60)
            if result.get('comprehensive_analysis'):
                print(result['comprehensive_analysis'])
            
            print("\n" + "="*60)
            print("✅ Resume evaluation completed!")
            
        else:
            print(f"\n❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to server.")
        print("Please make sure the server is running with: adk web")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    evaluate_resume_example() 