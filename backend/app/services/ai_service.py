import os
import json
import requests
import re
from google import genai
from dotenv import load_dotenv
from app.core.config import settings

load_dotenv()

# 1. Global Gemini Client Setup (Safe Init)
gemini_client = None
if settings.GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        print(f"⚠️ Gemini Client Init Warning: {e}")

class AIService:
    """
    Unified AI Service capable of switching between Gemini, OpenAI, and DeepSeek.
    """

    def _get_provider(self, requested_provider=None):
        # যদি রিকোয়েস্টে প্রোভাইডার আসে সেটা নিবে, নাহলে এনভায়রনমেন্ট ভেরিয়েবল, নাহলে ডিফল্ট 'gemini'
        if requested_provider:
            return requested_provider.lower()
        return settings.LLM_PROVIDER.lower() if hasattr(settings, 'LLM_PROVIDER') else "gemini"

    # --- Core Generation Methods ---

    def generate_market_sentiment_summary(self, headlines: str, asset: str, provider: str = None) -> str:
        system_prompt = f"""
        You are a crypto market analyst. 
        Analyze these headlines for {asset} and provide a concise 2-sentence summary of the current market sentiment (Bullish/Bearish/Neutral) and why.
        """
        user_content = f"Headlines: {headlines}"
        return self._route_request(system_prompt, user_content, provider)

    def generate_ai_strategy_templates(self, user_prompt: str = None, provider: str = None):
        system_instruction = """
        You are a professional quantitative trading architect. Generate 3 unique algorithmic trading strategies in JSON format.
        Strict Output Format (Array of Objects):
        [{"name": "...", "description": "...", "strategy_type": "...", "tags": [], "params": {}}]
        Return ONLY raw JSON. No markdown.
        """
        user_content = f"User Requirement: {user_prompt}" if user_prompt else "Generate 3 diverse strategies."
        
        response_text = self._route_request(system_instruction, user_content, provider)
        return self._clean_and_parse_json(response_text)

    def generate_strategy_code(self, user_prompt: str, provider: str = None) -> str:
        system_instruction = """
        You are an expert algorithmic trading developer using 'backtrader'. 
        Convert natural language ideas into a Python Backtrader Strategy.
        (Output ONLY raw Python code. No markdown.)
        """
        return self._route_request(system_instruction, f"User Strategy Idea: {user_prompt}", provider)

    def generate_visual_strategy(self, user_prompt: str, provider: str = None) -> dict:
        system_instruction = """
        You are an architect for a Visual Strategy Builder.
        Convert the idea into a JSON configuration of Nodes and Edges for a React Flow diagram.
        Output ONLY raw JSON.
        """
        response_text = self._route_request(system_instruction, f"User Idea: {user_prompt}", provider)
        return self._clean_and_parse_json(response_text, default={"nodes": [], "edges": []})

    # --- Internal Routing & API Calls ---

    def _route_request(self, system_prompt: str, user_content: str, provider: str = None) -> str:
        """
        Routes the request to the appropriate LLM provider.
        """
        active_provider = self._get_provider(provider)
        full_prompt = f"{system_prompt}\n\n{user_content}"

        try:
            # ✅ Syntax Error Fix: Ensure if/elif chain is clean
            if active_provider == "gemini":
                return self._call_gemini(full_prompt)
            
            elif active_provider == "openai":
                return self._call_openai_compatible(
                    settings.OPENAI_API_KEY, 
                    settings.OPENAI_BASE_URL, 
                    "gpt-4o", 
                    system_prompt, 
                    user_content
                )
            
            elif active_provider == "deepseek":
                return self._call_openai_compatible(
                    settings.DEEPSEEK_API_KEY, 
                    settings.DEEPSEEK_BASE_URL, 
                    "deepseek-chat", 
                    system_prompt, 
                    user_content
                )
            
            else:
                return f"❌ Error: Unknown Provider '{active_provider}'"

        except Exception as e:
            print(f"❌ AI Error ({active_provider}): {e}")
            return f"Error generating content via {active_provider}."

    def _call_gemini(self, full_prompt: str) -> str:
        if not gemini_client:
            return "❌ Gemini API Key missing or client init failed."
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )
        return response.text.strip()

    def _call_openai_compatible(self, api_key: str, base_url: str, model: str, system_msg: str, user_msg: str) -> str:
        if not api_key:
            return "❌ API Key missing for selected provider."
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                return f"API Error {response.status_code}: {response.text}"
        except Exception as e:
            return f"Connection Error: {str(e)}"

    def _clean_and_parse_json(self, text: str, default=None):
        if default is None: default = []
        try:
            # Clean markdown code blocks
            clean_text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {text[:100]}...")
            return default

# ✅ Create Global Instance
ai_service = AIService()

# ✅ Module-Level Wrapper Functions (Backwards Compatibility for strategies.py)
# strategies.py ফাইলটি মডিউল ফাংশন এক্সপেক্ট করে, তাই আমরা ক্লাসের মেথডগুলোকে র‍্যাপ করে দিচ্ছি।

def generate_ai_strategy_templates(user_prompt: str = None):
    return ai_service.generate_ai_strategy_templates(user_prompt)

def generate_strategy_code(user_prompt: str):
    return ai_service.generate_strategy_code(user_prompt)

def generate_visual_strategy(user_prompt: str):
    return ai_service.generate_visual_strategy(user_prompt)

def generate_market_sentiment_summary(headlines: str, asset: str):
    return ai_service.generate_market_sentiment_summary(headlines, asset)