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
    print("\n🤖 Running Sequential Agent Workflow...")
    print("   🔍 Step 1: Evaluation Agent - Comprehensive analysis")
    print("   📊 Step 2: Rating Agent - Scores + Improved Resume")
    
    try:
        # Make the request
        response = requests.post(f"{BASE_URL}/evaluate-resume", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Sequential workflow completed successfully!")
            
            # Get the reports
            evaluation_report = result.get('evaluation_report', '')
            rating_and_generation = result.get('rating_and_generation', '')
            
            # Show content lengths
            print(f"\n📊 Content Summary:")
            print(f"   📋 Evaluation Report: {len(evaluation_report)} characters")
            print(f"   📊 Rating & Generation: {len(rating_and_generation)} characters")
            
            # Display evaluation report from first agent
            if evaluation_report:
                print("\n" + "="*80)
                print("📋 FULL EVALUATION REPORT (Step 1 - Evaluation Agent)")
                print("="*80)
                print(evaluation_report)
                print("\n" + "="*80)
                print("📋 END OF EVALUATION REPORT")
                print("="*80)
            else:
                print("\n❌ No evaluation report received from first agent")
            
            # Display rating and generation from second agent
            if rating_and_generation:
                print("\n" + "="*80)
                print("📊 FULL RATING & IMPROVED RESUME (Step 2 - Rating Agent)")
                print("="*80)
                print(rating_and_generation)
                print("\n" + "="*80)
                print("📊 END OF RATING & IMPROVED RESUME")
                print("="*80)
            else:
                print("\n❌ No rating and generation received from second agent")
            
            # Summary
            print("\n" + "="*80)
            print("✅ SEQUENTIAL WORKFLOW SUMMARY")
            print("="*80)
            print("🔄 Workflow Type:", result.get('workflow_type', 'Unknown'))
            print("📝 Status:", "Success" if result.get('success') else "Failed")
            print("💬 Message:", result.get('message', ''))
            print("🎯 Both agents executed in sequence:")
            print("   1️⃣ Evaluation Agent → Comprehensive analysis")
            print("   2️⃣ Rating Agent → Used evaluation to provide scores & improved resume")
            print("="*80)
            
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