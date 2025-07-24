#!/usr/bin/env python3
"""
Example usage of the direct resume evaluation endpoint.
This demonstrates the main functionality: input resume text and job description,
get comprehensive evaluation and ratings from sequential agents.
"""

import requests
import json
import asyncio
import logging
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Server configuration
BASE_URL = "http://localhost:8000"

# Set up logging for tool usage
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def log_tool_usage_from_events(events):
    """
    Monitor events from agent execution and log tool usage.
    
    Args:
        events: Async iterator of events from runner.run_async()
    """
    tool_calls = []
    final_response = ""
    
    async for event in events:
        # Log general event information
        logger.info(f"Event: {event.author} - {event.id}")
        
        # Check if this event contains tool calls
        if event.content and event.content.parts:
            for part in event.content.parts:
                # Check for function calls (tool usage)
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    tool_call_info = {
                        "tool_name": function_call.name,
                        "tool_args": dict(function_call.args) if function_call.args else {},
                        "call_id": function_call.id,
                        "event_id": event.id,
                    }
                    tool_calls.append(tool_call_info)
                    
                    logger.info(f"🔧 TOOL CALLED: {function_call.name}")
                    logger.info(f"   Arguments: {tool_call_info['tool_args']}")
                    logger.info(f"   Call ID: {function_call.id}")
                
                # Check for function responses (tool results)
                if hasattr(part, 'function_response') and part.function_response:
                    function_response = part.function_response
                    logger.info(f"✅ TOOL RESPONSE: {function_response.name}")
                    logger.info(f"   Response: {str(function_response.response)[:200]}...")
                    logger.info(f"   Call ID: {function_response.id}")
        
        # Capture final response
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text
    
    # Log summary of tool usage
    if tool_calls:
        logger.info(f"📊 TOOL USAGE SUMMARY:")
        logger.info(f"   Total tool calls: {len(tool_calls)}")
        for call in tool_calls:
            logger.info(f"   - {call['tool_name']}: {call['tool_args']}")
    else:
        logger.info("📊 No tools were called during this execution")
    
    return final_response, tool_calls

async def test_agent_with_tool_logging():
    """
    Example of using ADK agents directly with tool usage logging.
    This shows how to monitor when and how tools are being used.
    """
    
    # Import the agents
    from src.agent.agent import evaluation_agent, rating_agent
    
    print("\n🔧 ADK Agent Direct Usage with Tool Logging Example")
    print("=" * 70)
    print("This example shows how to monitor tool usage in real-time")
    print("=" * 70)
    
    # Sample data
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
    
    # Create prompt for the agent
    prompt = f"""
    Please analyze this resume and job description combination:

    RESUME:
    {resume_text}

    JOB DESCRIPTION:
    {job_description}

    Please provide a comprehensive evaluation and use web search to research current market trends and salary insights for this role.
    """
    
    try:
        # Set up ADK components
        session_service = InMemorySessionService()
        runner = Runner(agent=evaluation_agent, app_name="resume-eval-test", session_service=session_service)
        
        # Create a session
        session = await session_service.create_session(
            app_name="resume-eval-test", 
            user_id="test_user", 
            session_id="test_session"
        )
        
        print("\n🚀 Running Evaluation Agent with Tool Logging...")
        print("👀 Watch the logs below to see tool usage in real-time:")
        print("-" * 50)
        
        # Create user content
        user_content = types.Content(
            role="user", 
            parts=[types.Part(text=prompt)]
        )
        
        # Run the agent and log tool usage
        events = runner.run_async(
            user_id="test_user",
            session_id="test_session", 
            new_message=user_content
        )
        
        response, tool_calls = await log_tool_usage_from_events(events)
        
        print("\n" + "=" * 70)
        print("📊 EXECUTION SUMMARY")
        print("=" * 70)
        print(f"✅ Agent executed successfully")
        print(f"🔧 Total tools called: {len(tool_calls)}")
        
        if tool_calls:
            print("\n🔧 TOOLS USED:")
            for i, call in enumerate(tool_calls, 1):
                print(f"   {i}. {call['tool_name']}")
                print(f"      Args: {call['tool_args']}")
        else:
            print("   No tools were used in this execution")
        
        print(f"\n📝 Response length: {len(response)} characters")
        print(f"📋 First 200 chars: {response[:200]}...")
        
        return response, tool_calls
        
    except Exception as e:
        logger.error(f"Error in agent execution: {e}")
        print(f"\n❌ Error: {e}")
        return None, []

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

async def main():
    """Main function to run all examples"""
    print("🚀 Resume Parser Testing Suite")
    print("=" * 50)
    print("Choose an example to run:")
    print("1. HTTP API Example (requires server running)")
    print("2. Direct ADK Agent Example with Tool Logging")
    print("3. Run both examples")
    
    choice = input("\nEnter your choice (1/2/3): ").strip()
    
    if choice == "1":
        evaluate_resume_example()
    elif choice == "2":
        await test_agent_with_tool_logging()
    elif choice == "3":
        print("\n" + "="*70)
        print("RUNNING HTTP API EXAMPLE")
        print("="*70)
        evaluate_resume_example()
        
        print("\n" + "="*70)
        print("RUNNING DIRECT ADK AGENT EXAMPLE")
        print("="*70)
        await test_agent_with_tool_logging()
    else:
        print("Invalid choice. Running HTTP API example by default.")
        evaluate_resume_example()

if __name__ == "__main__":
    asyncio.run(main()) 