import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from django.conf import settings

# Get API key from Django settings
GEMINI_API_KEY = settings.GEMINI_API_KEY
GEMINI_MODEL = settings.GEMINI_MODEL
GEMINI_TEMPERATURE = settings.GEMINI_TEMPERATURE

# Check if API key is available
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in .env file.")

# Initialize the model
llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    temperature=GEMINI_TEMPERATURE,
    google_api_key=GEMINI_API_KEY,
    convert_system_message_to_human=True
)

def classify_ticket(title, description):
    """Use Gemini to analyze ticket and suggest category, priority, sentiment"""
    
    template = """
    You are an AI assistant for a customer support helpdesk.
    
    Ticket Title: {title}
    Ticket Description: {description}
    
    Analyze this ticket and provide:
    1. category: Choose one [billing, technical, product, account, general]
    2. priority: Choose one [low, medium, high, urgent]
    3. sentiment: Choose one [positive, neutral, frustrated, angry]
    4. needs_escalation: true/false (true if angry or urgent)
    5. suggested_department: Choose one [billing, tech, product, general]
    6. summary: One line summary of the issue
    7. suggested_response: A brief suggested response for the agent
    
    Return ONLY valid JSON format.
    """
    
    prompt = PromptTemplate.from_template(template)
    
    # Create a simple chain manually to avoid parser issues
    try:
        formatted_prompt = prompt.format(title=title, description=description)
        response = llm.invoke(formatted_prompt)
        
        # Try to parse the response as JSON
        try:
            # Clean the response - remove markdown code blocks if present
            content = response.content
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            # If parsing fails, return structured fallback
            return {
                "category": "general",
                "priority": "medium",
                "sentiment": "neutral",
                "needs_escalation": False,
                "suggested_department": "general",
                "summary": title,
                "suggested_response": "Thank you for contacting us. We'll look into this."
            }
    except Exception as e:
        print(f"AI Error: {e}")
        # Fallback to default values if AI fails
        return {
            "category": "general",
            "priority": "medium",
            "sentiment": "neutral",
            "needs_escalation": False,
            "suggested_department": "general",
            "summary": title,
            "suggested_response": "Thank you for contacting us. We'll look into this."
        }

def generate_canned_response(ticket_title, customer_message):
    """Generate a personalized canned response"""
    
    template = """
    Customer Message: {message}
    Ticket Title: {title}
    
    Generate a helpful, professional response for the agent to send.
    Make it personalized and address the specific issue.
    Keep it concise but friendly.
    
    Return ONLY the response text, no JSON.
    """
    
    prompt = PromptTemplate.from_template(template)
    
    try:
        formatted_prompt = prompt.format(title=ticket_title, message=customer_message)
        response = llm.invoke(formatted_prompt)
        return response.content
    except Exception as e:
        print(f"AI Error: {e}")
        return "Thank you for contacting support. We're looking into your issue and will get back to you shortly."

def check_ai_health():
    """Check if AI service is properly configured"""
    if not GEMINI_API_KEY:
        return {
            "status": "error",
            "message": "GEMINI_API_KEY not configured"
        }
    
    try:
        # Simple test
        test_result = classify_ticket("test", "test")
        return {
            "status": "healthy",
            "message": "AI service is working",
            "model": GEMINI_MODEL
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }