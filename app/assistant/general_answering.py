from app.assistant.providers import create_chat_model


def answer_general_question(question: str) -> dict[str, str]:
    """Answer a general academic question without consulting college documents."""
    question = question.strip()
    if not question:
        raise ValueError("Question cannot be empty.")

    prompt = (
        "Answer the student's question clearly and concisely, with enough detail to be useful. "
        "Explain technical concepts at a college-student level. Do not claim to have access to "
        "college-specific information, and do not invent college rules, policies, schedules, fees, "
        "faculty information, or other college-specific facts. This assistant component answers "
        "general academic questions only.\n\n"
        f"Student question: {question}"
    )
    response = create_chat_model().invoke(prompt)
    return {"answer": str(response.content), "source": "general_llm"}
