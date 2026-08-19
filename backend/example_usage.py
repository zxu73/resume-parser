#!/usr/bin/env python3
"""
Example usage of the direct resume evaluation endpoint.
This demonstrates the main functionality: input resume text and job description,
get comprehensive evaluation and ratings from the LangGraph pipeline.
"""

import requests

# Server configuration
BASE_URL = "http://localhost:8000"

RESUME_TEXT = """
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

JOB_DESCRIPTION = """
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


def evaluate_resume_example():
    """Call the /evaluate-resume endpoint and print both agent outputs."""
    payload = {
        "resume_text": RESUME_TEXT,
        "job_description": JOB_DESCRIPTION,
    }

    print("🎯 Resume Evaluation Example")
    print("=" * 50)
    print("📝 Resume: 3 years experience, Python/JavaScript skills")
    print("💼 Job: Senior Python Developer, 5+ years required")
    print("\n🤖 Running Sequential Graph Workflow...")
    print("   🔍 Step 1: evaluate_only_graph - Comprehensive analysis")
    print("   📊 Step 2: rate_only_graph - Scores + bullet suggestions")

    try:
        response = requests.post(f"{BASE_URL}/evaluate-resume", json=payload)

        if response.status_code != 200:
            print(f"\n❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return

        result = response.json()
        print("\n✅ Sequential workflow completed successfully!")

        evaluation_report = result.get("evaluation_report", "")
        rating_and_generation = result.get("rating_and_generation", "")

        print("\n📊 Content Summary:")
        print(f"   📋 Evaluation Report: {len(evaluation_report)} characters")
        print(f"   📊 Rating & Generation: {len(rating_and_generation)} characters")

        if evaluation_report:
            print("\n" + "=" * 80)
            print("📋 FULL EVALUATION REPORT (Step 1 - Evaluation)")
            print("=" * 80)
            print(evaluation_report)
        else:
            print("\n❌ No evaluation report received from the evaluation graph")

        if rating_and_generation:
            print("\n" + "=" * 80)
            print("📊 FULL RATING & SUGGESTIONS (Step 2 - Rating)")
            print("=" * 80)
            print(rating_and_generation)
        else:
            print("\n❌ No rating and generation received from the rating graph")

        print("\n" + "=" * 80)
        print("✅ SEQUENTIAL WORKFLOW SUMMARY")
        print("=" * 80)
        print("🔄 Workflow Type:", result.get("workflow_type", "Unknown"))
        print("📝 Status:", "Success" if result.get("success") else "Failed")
        print("💬 Message:", result.get("message", ""))
        print("=" * 80)

    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to server.")
        print("Start it with: uvicorn src.agent.app:app --reload --port 8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    evaluate_resume_example()
