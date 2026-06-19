def _format_facts(key_facts: list[str]) -> str:
    return "\n".join(f"- {fact}" for fact in key_facts)


def basic_prompt(intent: str, key_facts: list[str], tone: str) -> str:
    
    facts_str = _format_facts(key_facts)
    return f"""Write a professional email.

Intent: {intent}
Key Facts:
{facts_str}
Tone: {tone}
"""


def advanced_prompt(intent: str, key_facts: list[str], tone: str) -> str:

    facts_str = _format_facts(key_facts)
    return f"""You are an experienced corporate communication specialist.
Follow these steps:
1. Understand the user's intent.
2. Include all key facts naturally.
3. Adjust the writing style according to the tone.
4. Produce a professional email with a subject line.

Intent:
{intent}

Key Facts:
{facts_str}

Tone:
{tone}

Generate the final email.
"""
