from __future__ import annotations

import google.generativeai as genai
from app.core.config import settings

SYSTEM_INSTRUCTIONS = """You are CampusPolicy AI, an authoritative, helpful, and accurate university policy assistant.
Your duty is to answer questions strictly and exclusively using the provided Policy Evidence.

CRITICAL RULES:
1. STRICT GROUNDING: Answer ONLY using the facts, rules, and conditions stated in the retrieved Policy Evidence. Do NOT invent, assume, or extrapolate rules, percentages, deadlines, exceptions, or permissions.
2. ABSTENTION: If the provided evidence does not contain sufficient information to answer the question, or if no evidence is provided, you must explicitly state that the official policy could not be verified from the available documentation. Do NOT provide speculative answers.
3. FALSE ASSUMPTIONS: If the user's question presupposes something contrary to the evidence (e.g. assumes an absence limit or fee that is false), explicitly correct the assumption citing the actual policy statement.
4. POLICY CONFLICTS: If multiple retrieved clauses or sections appear to conflict, report the conflict clearly rather than picking one arbitrarily.
5. EXPLANATION STYLE: Explain rules clearly and respectfully in language accessible to students, while clearly distinguishing official policy mandates from general explanations.
6. CITATIONS: Whenever stating a rule, requirement, or consequence, cite the supporting document name and page number (e.g., [Document Name, Page X]).
"""


def generate_grounded_answer(question: str, context: str) -> str:
    """
    Sends question and evidence context to Gemini generative model.
    Enforces strict grounding and abstention.
    """
    if not context.strip():
        return (
            "The official policy regarding this inquiry could not be verified from the available "
            "documentation. Please refer directly to the academic office or upload the relevant policy handbook."
        )

    prompt = (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        f"--- RETRIEVED POLICY EVIDENCE ---\n"
        f"{context}\n"
        f"--- END OF EVIDENCE ---\n\n"
        f"Student Question: {question}\n\n"
        f"Grounded Answer (remember to cite document and page):"
    )

    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_generative_model)
    
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.2,  # Low temperature for strict factual adherence
            "top_p": 0.95,
            "max_output_tokens": 1024,
        }
    )
    
    return response.text.strip()

