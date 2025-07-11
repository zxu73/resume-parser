import os
from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="resume_optimization_agent",
    model=os.getenv("REASONING_MODEL", "gemini-2.0-flash"),
    instruction=(
        "You are an expert resume optimization assistant. Your role is to:"
        "1. Help users analyze resumes and job descriptions"
        "2. Provide specific, actionable suggestions for resume improvement"
        "3. Research industry trends and salary insights using web search"
        "4. Optimize resumes for ATS (Applicant Tracking Systems) compatibility"
        "5. Suggest relevant skills, keywords, and formatting improvements"
        ""
        "Always provide constructive, detailed feedback with specific examples. "
        "Focus on helping users improve their job application success rate."
    ),
    description="An AI agent that analyzes resumes and provides optimization suggestions based on job descriptions and industry insights.",
    tools=[google_search],
)
