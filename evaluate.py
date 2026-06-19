import csv
import json
import os
import sys
import time

from google import genai
from google.genai import errors as genai_errors

from prompts import advanced_prompt
from metrics import fact_recall_score, tone_accuracy_score, conciseness_score

MODEL = "gemini-2.5-flash-lite"
SCENARIOS_FILE = "scenarios.json"
OUTPUT_FILE = "results.csv"

SECONDS_BETWEEN_SCENARIOS = 5
MAX_RETRIES = 5

FIELDNAMES = [
    "scenario_id", "intent", "tone",
    "fact_recall", "tone_accuracy", "conciseness", "average",
    "generated_email",
]


def load_scenarios(path: str) -> list:
    with open(path, "r") as f:
        return json.load(f)


def load_completed_ids(path):
    if not os.path.exists(path):
        return set()
    done = set()
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            done.add(int(row["scenario_id"]))
    return done


def append_row(path, row):
    file_exists = os.path.exists(path) and os.path.getsize(path) > 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def call_with_retry(fn, *args, **kwargs):
    delay = 10
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except genai_errors.APIError as e:
            msg = str(e)
            if "PerDay" in msg:
                raise  # daily cap hit -- retrying won't help
            is_retryable = any(code in msg for code in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))
            if is_retryable and attempt < MAX_RETRIES:
                print(f"  Transient API error. Waiting {delay}s before retry {attempt}/{MAX_RETRIES}...")
                time.sleep(delay)
                delay *= 2
            else:
                raise


def generate_with_model_b(client, scenario: dict) -> str:
    prompt = advanced_prompt(scenario["intent"], scenario["key_facts"], scenario["tone"])
    response = call_with_retry(client.models.generate_content, model=MODEL, contents=prompt)
    return response.text or ""


def evaluate_scenario(client, scenario: dict) -> dict:
    generated_email = generate_with_model_b(client, scenario)

    fact_score    = fact_recall_score(generated_email, scenario["key_facts"])
    tone_score    = tone_accuracy_score(generated_email, scenario["tone"], client, model=MODEL)
    concise_score = conciseness_score(generated_email)
    average       = round((fact_score + tone_score + concise_score) / 3, 2)

    return {
        "scenario_id":     scenario["id"],
        "intent":          scenario["intent"],
        "tone":            scenario["tone"],
        "fact_recall":     fact_score,
        "tone_accuracy":   tone_score,
        "conciseness":     concise_score,
        "average":         average,
        "generated_email": generated_email,
    }


def print_summary():
    if not os.path.exists(OUTPUT_FILE):
        print("No results yet.")
        return
    with open(OUTPUT_FILE, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return
    overall_average = round(sum(float(r["average"]) for r in rows) / len(rows), 2)
    print(f"\n{len(rows)} scenario(s) in {OUTPUT_FILE}. Overall average score so far: {overall_average}")


def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "ERROR: GEMINI_API_KEY not set. Run:\n"
            "  set GEMINI_API_KEY=your_key_here\n"
            "then re-run this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    client    = genai.Client()
    scenarios = load_scenarios(SCENARIOS_FILE)
    completed = load_completed_ids(OUTPUT_FILE)

    if completed:
        print(f"Resuming: {len(completed)} scenario(s) already in {OUTPUT_FILE}, skipping those.\n")

    try:
        for i, scenario in enumerate(scenarios):
            if scenario["id"] in completed:
                continue

            print(f"Evaluating scenario {scenario['id']}: {scenario['intent']!r} ...")
            row = evaluate_scenario(client, scenario)
            append_row(OUTPUT_FILE, row)
            print(
                f"  fact_recall={row['fact_recall']}  "
                f"tone_accuracy={row['tone_accuracy']}  "
                f"conciseness={row['conciseness']}  "
                f"average={row['average']}  [saved]"
            )
            if i < len(scenarios) - 1:
                time.sleep(SECONDS_BETWEEN_SCENARIOS)

    except genai_errors.APIError as e:
        print(f"\nStopped early due to an API error: {e}\n")
        print(f"Progress so far IS saved in {OUTPUT_FILE}.")
        print("Just run `python evaluate.py` again later (e.g. after the daily quota resets) to continue.")
        print_summary()
        sys.exit(1)

    print(f"\nAll scenarios complete. Saved to {OUTPUT_FILE}")
    print_summary()


if __name__ == "__main__":
    main()
