"""System prompts for different conversation modes."""

BASE_SYSTEM_PROMPT = """You're LIRA, a friendly English buddy. Keep responses to ONE short sentence. Be warm and curious. Level: {level}"""

MODE_PROMPTS = {
    "free_talk": """Chat naturally. React briefly, ask one question.""",
    "corrective": """Chat, then quick fix: "Try saying X instead of Y!" """,
    "roleplay": """Stay in character: {scenario}""",
    "guided": """Ask simple questions for {level}. Be encouraging.""",
}

ROLEPLAY_SCENARIOS = {
    "job_interview": "You are a hiring manager conducting a job interview for a marketing position.",
    "restaurant": "You are a waiter at a restaurant taking an order.",
    "hotel": "You are a hotel receptionist helping a guest check in.",
    "airport": "You are an airline staff member helping a passenger with their flight.",
    "shopping": "You are a sales assistant helping a customer find clothes.",
    "doctor": "You are a doctor conducting a routine health checkup.",
}


def get_system_prompt(mode: str, level: str, scenario: str | None = None) -> str:
    """
    Generate the complete system prompt based on mode and level.

    @param mode - Conversation mode (free_talk, corrective, roleplay, guided)
    @param level - CEFR level (A2, B1, B2, C1)
    @param scenario - Optional roleplay scenario key
    @returns Complete system prompt string
    """
    base = BASE_SYSTEM_PROMPT.format(level=level)

    mode_prompt = MODE_PROMPTS.get(mode, MODE_PROMPTS["free_talk"])

    if mode == "roleplay" and scenario:
        scenario_desc = ROLEPLAY_SCENARIOS.get(scenario, scenario)
        mode_prompt = mode_prompt.format(scenario=scenario_desc)
    elif mode == "guided":
        mode_prompt = mode_prompt.format(level=level)

    return f"{base}\n{mode_prompt}"
