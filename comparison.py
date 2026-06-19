import csv
import json
import os
import sys
import time

from google import genai
from google.genai import errors as genai_errors

from prompts import basic_prompt, advanced_prompt
from metrics import fact_recall_score, tone_accuracy_score, conciseness_score

MODEL = "gemini-2.5-flash-lite"
SCENARIOS_FILE = "scenarios.json"
OUTPUT_FILE = "comparison.csv"

SECONDS_BETWEEN_CALLS = 5
MAX_RETRIES = 5

STRATEGIES = {
    "Model A (Basic Prompt)": basic_prompt,
    "Model B (Role-Play + CoT)": advanced_prompt,
}

FIELDNAMES = [
    "scenario_id", "intent", "tone", "strategy",
    "fact_recall", "tone_accuracy", "conciseness", "average",
    "generated_email",
]


def load_scenarios(path):
    with open(path, "r") as f:
        return json.load(f)


def load_completed_pairs(path):
    """Returns a set of (scenario_id, strategy) pairs already saved in the CSV,
    so we can skip them on a re-run instead of burning quota redoing them."""
    if not os.path.exists(path):
        return set()
    completed = set()
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            completed.add((int(row["scenario_id"]), row["strategy"]))
    return completed


def append_row(path, row):
    """Appends a single row to the CSV, writing the header first if the file is new/empty."""
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
                raise  
            is_retryable = any(code in msg for code in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))
            if is_retryable and attempt < MAX_RETRIES:
                print(f"  Transient API error. Waiting {delay}s before retry {attempt}/{MAX_RETRIES}...")
                time.sleep(delay)
                delay *= 2
            else:
                raise


def run_strategy(client, prompt_fn, scenario):
    prompt = prompt_fn(scenario["intent"], scenario["key_facts"], scenario["tone"])
    response = call_with_retry(client.models.generate_content, model=MODEL, contents=prompt)
    generated_email = response.text or ""

    fact_score    = fact_recall_score(generated_email, scenario["key_facts"])
    tone_score    = tone_accuracy_score(generated_email, scenario["tone"], client, model=MODEL)
    concise_score = conciseness_score(generated_email)
    average       = round((fact_score + tone_score + concise_score) / 3, 2)

    return {
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

    totals = {name: {"fact_recall": [], "tone_accuracy": [], "conciseness": [], "average": []}
              for name in STRATEGIES}

    with open(OUTPUT_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            strat = row["strategy"]
            if strat not in totals:
                continue
            for k in ("fact_recall", "tone_accuracy", "conciseness", "average"):
                totals[strat][k].append(float(row[k]))

    print("\n=== Aggregate Summary (based on comparison.csv so far) ===")
    overall_avgs = {}
    for strat_name, vals in totals.items():
        if not vals["average"]:
            print(f"\n{strat_name}: no completed rows yet")
            continue
        print(f"\n{strat_name}  ({len(vals['average'])} scenarios completed)")
        for metric, scores in vals.items():
            print(f"  avg {metric}: {round(sum(scores)/len(scores), 2)}")
        overall_avgs[strat_name] = sum(vals["average"]) / len(vals["average"])

    if len(overall_avgs) == len(STRATEGIES):
        weaker = min(overall_avgs, key=overall_avgs.get)
        weaker_metrics = {m: sum(totals[weaker][m]) / len(totals[weaker][m])
                          for m in ("fact_recall", "tone_accuracy", "conciseness")}
        weakest = min(weaker_metrics, key=weaker_metrics.get)
        print(f"\nLower-scoring strategy so far: {weaker}")
        print(f"Weakest metric for it        : {weakest} (avg {round(weaker_metrics[weakest], 2)})")


def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set.\n  set GEMINI_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(1)

    client    = genai.Client()
    scenarios = load_scenarios(SCENARIOS_FILE)
    completed = load_completed_pairs(OUTPUT_FILE)

    if completed:
        print(f"Resuming: {len(completed)} (scenario, strategy) pairs already in {OUTPUT_FILE}, skipping those.\n")

    total_pairs = len(scenarios) * len(STRATEGIES)
    done_count = len(completed)

    try:
        for scenario in scenarios:
            for strat_name, prompt_fn in STRATEGIES.items():
                pair = (scenario["id"], strat_name)
                if pair in completed:
                    continue

                print(f"\nScenario {scenario['id']}: {scenario['intent']!r}  |  {strat_name}")
                result = run_strategy(client, prompt_fn, scenario)
                row = {
                    "scenario_id": scenario["id"],
                    "intent":      scenario["intent"],
                    "tone":        scenario["tone"],
                    "strategy":    strat_name,
                    **result,
                }
                append_row(OUTPUT_FILE, row)
                done_count += 1
                print(f"  fact={result['fact_recall']} tone={result['tone_accuracy']} "
                      f"concise={result['conciseness']} avg={result['average']}  "
                      f"[{done_count}/{total_pairs} saved]")
                time.sleep(SECONDS_BETWEEN_CALLS)

    except genai_errors.APIError as e:
        print(f"\nStopped early due to an API error: {e}\n")
        print(f"Progress so far IS saved in {OUTPUT_FILE} ({done_count}/{total_pairs} pairs done).")
        print("Just run `python comparison.py` again later (e.g. after the daily quota resets) to continue.")
        print_summary()
        sys.exit(1)

    print(f"\nAll {total_pairs} pairs complete. Results in {OUTPUT_FILE}")
    print_summary()


if __name__ == "__main__":
    main()
