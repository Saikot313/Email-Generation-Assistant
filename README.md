<<<<<<< HEAD
# Email Generation Assistant

AI Engineer Candidate Assessment — all 3 parts in one repository.

## Folder Structure

```
Email_Generation_Assistant/
├── app.py            # Streamlit UI (Part 1)
├── prompts.py        # Basic prompt (Model A) + Role-Play+CoT prompt (Model B)
├── scenarios.json    # 10 test scenarios with human reference emails
├── evaluate.py       # Runs Model B on all 10 scenarios → results.csv
├── metrics.py        # 3 custom metrics: Fact Recall, Tone Accuracy, Conciseness
├── comparison.py     # Model A vs Model B → comparison.csv
├── results.csv       # Output of evaluate.py (generated after running)
├── comparison.csv    # Output of comparison.py (generated after running)
├── report.pdf        # Final report PDF
├── requirements.txt
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
```

## Part 1 — Run the Streamlit App

```bash
streamlit run app.py
```

Enter Intent, Key Facts, Tone → click Generate Email.

## Part 2 — Evaluation (10 Scenarios + 3 Custom Metrics)

```bash
python evaluate.py
```

Outputs `results.csv` with Fact Recall, Tone Accuracy, Conciseness scores for all 10 scenarios.

## Part 3 — Model Comparison

```bash
python comparison.py
```

Outputs `comparison.csv` comparing Model A (basic prompt) vs Model B (Role-Play + CoT) across all 10 scenarios.

## Prompting Technique (Part 2)

**Role-Playing + Chain-of-Thought (CoT)** — see `prompts.py → advanced_prompt()`.

## Custom Metrics (Part 3)

| # | Metric | Method | Score Range |
|---|--------|--------|-------------|
| 1 | Fact Recall | Keyword overlap (pure Python) | 0–100 |
| 2 | Tone Accuracy | LLM-as-a-Judge (Gemini) | 0–100 |
| 3 | Conciseness | Word count band (60–150 words) | 0–100 |

See `metrics.py` for full logic and rationale.
=======
# Email_Generation-Assistant
AI-powered Email Generation Assistant built with Python, Streamlit, and Gemini API. Generates professional emails from user intent, key facts, and tone using advanced prompt engineering (Role-Playing + Chain-of-Thought), with custom evaluation metrics and model comparison.
>>>>>>> 9ac6a3a8feb35c15f8f4b11ef00bea5d77f706ce
