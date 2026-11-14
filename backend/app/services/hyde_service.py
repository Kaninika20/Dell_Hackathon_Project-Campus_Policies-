from __future__ import annotations

import google.generativeai as genai
from app.core.config import settings

HYDE_SYSTEM_PROMPT = """You are a policy document drafting assistant.
Your sole job is to write a short hypothetical excerpt from an official university policy handbook that addresses the user's question.

CRITICAL INSTRUCTIONS:
1. Write in formal, administrative, legalistic policy language (e.g. "Section ... Attendance Condonation on Medical Grounds", "Regulations Governing Student Conduct").
2. DO NOT invent specific numbers, percentages, fees, or penalty codes unless they are common standard terms.
3. This is purely a hypothetical passage intended to capture the vocabulary and semantic tone of official campus regulations.
4. Keep the output concise (2-4 sentences max).
5. DO NOT provide conversational greetings, disclaimers, or explanations. Return ONLY the hypothetical policy text.
"""


def generate_hypothetical_document(query: str) -> str:
    """
    Generates a hypothetical administrative policy passage to improve retrieval
    of official policy clauses from informal/casual student queries.
    """
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_generative_model)

    prompt = f"{HYDE_SYSTEM_PROMPT}\n\nStudent Query: {query}\n\nHypothetical Policy Excerpt:"

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,
                "top_p": 0.95,
                "max_output_tokens": 200,
            }
        )
        hypo_text = response.text.strip()
        return hypo_text if hypo_text else query
    except Exception:
        # Fallback to original query if LLM generation fails or times out
        return query

