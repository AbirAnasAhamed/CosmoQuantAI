from google import genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

# API Key লোড করা
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def generate_ai_strategy_templates(user_prompt: str = None):
    
    # বেস ইনস্ট্রাকশন
    system_instruction = """
    You are a professional quantitative trading architect. Generate 3 unique algorithmic trading strategies in JSON format.
    
    Strict Output Format (Array of Objects):
    [
        {
            "name": "Creative Name",
            "description": "Technical explanation...",
            "strategy_type": "Choose one from [SMA Crossover, RSI Crossover, MACD Crossover, Bollinger Bands, EMA Crossover, Grid Trading]",
            "tags": ["Tag1", "Tag2"],
            "params": { ...valid params matching standard indicators... }
        }
    ]
    Return ONLY raw JSON. No markdown.
    """

    # যদি ইউজার প্রম্পট দেয়, তবে সেটি যুক্ত করবো
    if user_prompt:
        content = f"{system_instruction}\n\nUser Specific Requirement: Create strategies based on this idea -> '{user_prompt}'"
    else:
        content = f"{system_instruction}\n\nGenerate 3 diverse strategies (e.g. one trend, one reversal, one volatility based)."

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=content
        )
        
        json_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(json_text)
    
    except Exception as e:
        print(f"AI Generation Error: {e}")
        return []