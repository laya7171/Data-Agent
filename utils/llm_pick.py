from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()
#for this project i'm using the lower end model for all 3 cases if needed any high end model can be subsituted
def pick_llm(model_level: str):
    """
    Picks the appropriate LLM based on the level of the question."""

    if model_level.lower() == "low":
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            temperature=0.2,
            max_output_tokens=1024,
        )
    elif model_level.lower() == "medium":
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            temperature=0.2,
            max_output_tokens=1024,
        )
    elif model_level.lower() == "high":
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            temperature=0.2,
            max_output_tokens=1024,
        )
    else:
        raise ValueError("Invalid model level. Please choose 'low', 'medium', or 'high'.")

