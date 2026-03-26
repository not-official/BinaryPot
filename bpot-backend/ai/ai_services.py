import asyncio
import os
from typing import List, Dict
from dotenv import load_dotenv
from ai_prompt import SYSTEM_PROMPT_TERMINAL
from google import genai
from google.genai import types
from fake_fs import FakeFS

# ---- Mocked AI Service (for learning) ---- #
load_dotenv()

class AIService:
    def __init__(self):
        # Later we’ll load OPENAI_API_KEY and MODEL here
        self.model = os.getenv("GOOGLE_API_KEY")
        # self.api_key = os.getenv("OPENAI_API_KEY", "mocked-key")
        self.system_prompt = SYSTEM_PROMPT_TERMINAL
        self.client = genai.Client()

    async def generate_with_fs(self, user_input: str, fs_state: dict):
        """
        Includes FS snapshot in the system prompt so AI behaves consistently.
        """
        await asyncio.sleep(1)
        system_prompt = self.system_prompt + f"\n\n[FILESYSTEM STATE]\n{fs_state}\n"
        # response = await self.client.responses.create(
        # model="gpt-4.1-mini",
        config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        )
        response = self.client.models.generate_content(
        model="gemini-2.5-flash",
        contents= user_input,
        config=config
        )
        return response.text


async def main():
        ai = AIService()
        fs = FakeFS()

        output = await ai.generate_with_fs(cmd, fs.fs)
        print(output)



        print() 
# Expected Output: "It's 4, obviously. Next time try something that requires an IQ above room temperature."

if __name__ == "__main__":
    asyncio.run(main())



# 1. Initialize the client (assumes GEMINI_API_KEY is set as an environment variable)
