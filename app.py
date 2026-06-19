
import os
import streamlit as st
from google import genai
from prompts import advanced_prompt

MODEL = "gemini-2.5-flash-lite"

# Page config 
st.set_page_config(page_title="Email Generation Assistant", page_icon="✉️", layout="centered")

st.title("✉️ Email Generation Assistant")
st.markdown(
    "Enter the three inputs below and click **Generate Email** to get a "
    "professional, ready-to-send email powered by Gemini."
)

# API key 
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="Paste your GEMINI_API_KEY here...",
        help="Get a free key at https://aistudio.google.com/app/apikey",
    )

st.divider()

# Inputs
col1, col2 = st.columns([2, 1])
with col1:
    intent = st.text_input(
        "Intent",
        placeholder="e.g. Follow up after meeting",
    )
with col2:
    tone = st.selectbox(
        "Tone",
        ["Formal", "Casual", "Urgent", "Empathetic"],
    )

facts_raw = st.text_area(
    "Key Facts  (one per line)",
    placeholder="- Meeting held on Monday\n- Need proposal before June 25\n- Budget around $10,000",
    height=130,
)

# Generate 
if st.button("⚡ Generate Email", type="primary", use_container_width=True):
    key_facts = [line.lstrip("•-– ").strip() for line in facts_raw.strip().splitlines() if line.strip()]

    if not api_key:
        st.error("Please enter your Gemini API Key above.")
    elif not intent.strip():
        st.error("Please fill in the Intent field.")
    elif not key_facts:
        st.error("Please add at least one Key Fact.")
    else:
        with st.spinner("Generating your email..."):
            try:
                client = genai.Client(api_key=api_key)
                prompt = advanced_prompt(intent.strip(), key_facts, tone)
                response = client.models.generate_content(model=MODEL, contents=prompt)
                generated = response.text or ""

                st.success("Email generated!")
                st.subheader("📧 Generated Email")
                st.code(generated, language=None)

                st.download_button(
                    "⬇️ Download as .txt",
                    data=generated,
                    file_name="generated_email.txt",
                    mime="text/plain",
                )

                with st.expander("Prompting Technique Used"):
                    st.markdown(
                        "**Role-Playing + Chain-of-Thought (CoT)**\n\n"
                        "- The model is given the persona of an *experienced corporate "
                        "communication specialist*, anchoring its vocabulary and judgment "
                        "to that of a skilled human writer.\n"
                        "- Four explicit reasoning steps (understand intent → include facts "
                        "→ adjust tone → write email) force the model to plan before "
                        "drafting, reducing dropped facts and tone mismatches."
                    )
            except Exception as exc:
                st.error(f"API error: {exc}")

st.divider()
st.caption("Part 1 of the AI Engineer Candidate Assessment — Email Generation Assistant")
