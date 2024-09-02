import os
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai
import anthropic
from groq import Groq
import logging
import asyncio

# Suppress HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

# Initialize API clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class ModelAPI:
    def __init__(self, provider, model, temperature=0.1):
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        if self.provider == "openai":
            self.client = OpenAI()
        elif self.provider == "groq":
            self.client = Groq()

    async def generate_text(self, prompt, system_prompt=None, max_tokens=3000):
        try:
            if self.provider == "openai":
                messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
                messages.append({"role": "user", "content": prompt})
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content

            elif self.provider == "google":
                model = genai.GenerativeModel(self.model)
                content = [system_prompt, prompt] if system_prompt else prompt
                response = model.generate_content(
                    content,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature
                    ),
                    stream=True
                )
                for chunk in response:
                    yield chunk.text

            elif self.provider == "anthropic":
                messages = [{"role": "user", "content": prompt}]
                stream = anthropic_client.messages.stream(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,  # Use 'system' parameter instead of a message
                    messages=messages
                )
                with stream as stream:
                    for text in stream.text_stream:
                        yield text

            elif self.provider == "groq":
                messages = [{"role": "system", "content": system_prompt or "You are a helpful assistant."}]
                messages.append({"role": "user", "content": prompt})
                stream = self.client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    top_p=1,
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content

            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            print(f"Error generating text with {self.provider} {self.model}: {str(e)}")
            raise

def get_api(provider, model, temperature=0.1):
    return ModelAPI(provider, model, temperature)