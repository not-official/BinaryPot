import json
import asyncio
import os
from typing import List, Dict
from dotenv import load_dotenv
from ai_prompt import SYSTEM_PROMPT_TERMINAL, get_system_prompt
from google import genai
from google.genai import types
import ai_cache

# ---- Mocked AI Service (for learning) ---- #
load_dotenv()






 # Later we’ll load OPENAI_API_KEY and MODEL here
model = os.getenv("GOOGLE_API_KEY")
# self.api_key = os.getenv("OPENAI_API_KEY", "mocked-key")
system_prompt = "You are a AI assistant to help terminal"
client = genai.Client()

async def get_ai_response( sys_prompt: str,user_input: str):
        """
        Includes FS snapshot in the system prompt so AI behaves consistently.
        
        Checks cache first, then sends prompt to AI if needed.
    """
    # 1. CHECK CACHE FIRST (Module 4)
        cached = ai_cache.get_cached_response(user_input)
        if cached:
                print(f"[AIService] Cache HIT for: '{user_input}'")
                print(f"[AIService] Cached Response: '{cached}'\n")
                return cached

    # 2. If not in cache, proceed with API call
        
        try:
                print(f"[AIService] Cache MISS for: '{user_input}'")
                print(f"system_prompt: '{sys_prompt}'\n")
                print(f"user_input: '{user_input}'\n")
                # response = await self.client.responses.create(
                # model="gpt-4.1-mini",
                config = types.GenerateContentConfig(
                system_instruction=sys_prompt,
                )
                response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents= user_input,
                config=config
                )
                answer = response.text
                ai_cache.set_cached_response(user_input, answer)
                print(f"[AIService] AI Response: '{answer}'\n")
                if answer is None:
                        answer = ""
                return answer
        
        except Exception as e:
                print(f"[AIService] Error: {e}")
                return None # Return empty string on error so honeypot doesn't crash
