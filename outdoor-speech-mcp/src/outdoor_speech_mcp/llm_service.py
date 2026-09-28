import os

from openai import OpenAI


class LLMService:
    def ask(self, prompt: str, model: str | None = None) -> str:
        """Send a prompt to the configured OpenAI model and return its text response."""
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        selected_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = OpenAI(api_key=api_key).responses.create(
            model=selected_model,
            input=prompt,
        )
        if not response.output_text:
            raise RuntimeError("The OpenAI model returned no text")
        return response.output_text