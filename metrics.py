import re

# Metric 1: Fact Recall Score

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "for", "and", "or", "with", "at", "by", "from",
    "as", "that", "this", "it", "its", "their", "our", "your", "we", "you",
    "they", "he", "she", "i", "need", "needs", "must", "will", "would",
    "should", "can", "could", "due", "before", "after", "around", "about",
    "approximately", "roughly", "has", "have", "had", "not", "no",
}


def _keywords(text: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z0-9$%]+", text.lower())
    return {t for t in tokens if t not in _STOPWORDS and len(t) > 1}


def fact_recall_score(generated_email: str, key_facts: list[str]) -> float:
    if not key_facts:
        return 100.0

    email_lower = generated_email.lower()
    recalled = 0

    for fact in key_facts:
        fact_keywords = _keywords(fact)
        if not fact_keywords:
            continue
        hits = sum(1 for kw in fact_keywords if kw in email_lower)
        overlap_ratio = hits / len(fact_keywords)
        if overlap_ratio >= 0.5:
            recalled += 1

    return round((recalled / len(key_facts)) * 100, 2)



# Metric 2: Tone Accuracy Score (LLM-as-a-Judge)


_JUDGE_PROMPT_TEMPLATE = """You are an expert writing coach evaluating whether an email matches a target tone.

Target Tone: {tone}

Email:
\"\"\"
{email}
\"\"\"

On a scale of 0 to 100, how well does this email's word choice, sentence structure, and overall feel match the target tone of "{tone}"? 100 means a perfect match for an experienced professional writer; 0 means it reads as the opposite tone.

Respond with ONLY a single integer between 0 and 100. No words, no explanation."""


def tone_accuracy_score(
    generated_email: str,
    tone: str,
    client,
    model: str = "gemini-2.5-flash-lite",
) -> float:
    import time
    from google.genai import errors as genai_errors

    prompt = _JUDGE_PROMPT_TEMPLATE.format(tone=tone, email=generated_email)

    delay = 10
    response = None
    for attempt in range(1, 6):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            break
        except genai_errors.APIError as e:
            is_retryable = any(code in str(e) for code in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))
            if is_retryable and attempt < 5:
                time.sleep(delay)
                delay *= 2
            else:
                raise

    raw = (response.text or "").strip()

    match = re.search(r"\d+", raw)
    if not match:
        raise ValueError(f"Judge did not return a parseable score: {raw!r}")

    score = int(match.group())
    return float(max(0, min(100, score)))



# Metric 3: Conciseness Score


def conciseness_score(
    generated_email: str,
    ideal_min: int = 60,
    ideal_max: int = 150,
) -> float:
    word_count = len(generated_email.split())

    if ideal_min <= word_count <= ideal_max:
        return 100.0

    if word_count < ideal_min:
        deficit = ideal_min - word_count
        score = max(0, 100 - deficit * 2)
    else:
        excess = word_count - ideal_max
        score = max(0, 100 - excess * 1.5)

    return round(score, 2)
