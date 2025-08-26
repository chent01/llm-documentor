# Brief: Gathers component requirement files from a directory and attempts to generate a list of IEC 62304 compliant system requirements

import os
import requests
from pathlib import Path

# Configuration

# DeepMentor box
LLM_API_URL = "http://192.168.2.163:8000/v1/chat/completions"  # OpenAI-compatible endpoint
MODEL_NAME = "/app/models"                                     # Replace with your model name

# LM Studio
# LLM_API_URL = "http://127.0.0.1:1234/v1/chat/completions"  # OpenAI-compatible endpoint
# MODEL_NAME = "openai/gpt-oss-20b"                          # Replace with your model name

ROOT_DIR = "../output/gpt-oss-20b/deviceSelection/summaries"                                         # Replace with directory of component requirement files
SYSTEM_REQUIREMENTS_FILE = "../output/deepseek-coder-v2/deviceSelection/systemRequirements.md"       # Replace with path of Architecture Design file output 
IGNORED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".exe", ".bin", ".woff", ".ttf", ".pdf"}

def is_text_file(file_path: Path) -> bool:
    return file_path.suffix.lower() not in IGNORED_EXTENSIONS

# Call OpenAI-compatible chat endpoint at /v1/chat/completions.
def call_llm(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are an expert IEC 62304 consultant preparing documents for a hearing aid fitting software project. The software needs to prove compliance to TGA Australia as a Class IIa Software as Medical Device (SaMD)."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    try:
        response = requests.post(LLM_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError) as e:
        return f"[ERROR] LLM request failed or malformed response: {e}"

def summarize_file(file_path: Path) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            content = file.read()
    except Exception as e:
        return f"[ERROR] Failed to read file {file_path}: {e}"

    return content

def collect_all_summaries() -> list:
    all_summaries = []
    for root, _, files in os.walk(ROOT_DIR):
        for filename in files:
            full_path = Path(root) / filename

            if not is_text_file(full_path):
                continue

            summary = summarize_file(full_path)
            all_summaries.append(f"## {filename}\n\n{summary}\n")

    return all_summaries

def generate_system_requirements_list(summaries: list):
    prompt = f"""
        You are analyzing a list of software components requirements to understand the system requirements the software design was tailored to.
        Based on the following file summaries, align with IEC 62304 compliance and merge similar or redundant requirements where possible for each level being careful to preserve important nuance and subtle differences.

        - Be concise. 
        - Use “shall” to indicate mandatory requirements.
        - Be specific and measurable (avoid vague words like “fast”, “user-friendly”, “easy”).
        - Keep one requirement per statement — split if needed.
        - Include conditions and constraints where relevant (e.g., timing, range, accuracy).
        - Use consistent terminology aligned with your glossary.
        - Return your response in Markdown format, completing the below template.

        Use Markdown formatting and provide a comprehensive list following the below template

        Template
        ## System Requirements
        - The system shall <specific function or performance metric> [within defined limits] [under specified conditions].

        Here are the file summaries:
        {summaries}""" # Truncate if needed
    
    architecture_summary = call_llm(prompt)
    
    with open(SYSTEM_REQUIREMENTS_FILE, "w", encoding="utf-8") as file:
        file.write(architecture_summary)

    print(f"\n[✓] Requirements summary written to: {SYSTEM_REQUIREMENTS_FILE}")

def main():
    print("[*] Collecting summaries...\n")
    summaries = collect_all_summaries()
    print("\n[*] Generating system requirements overview...\n")
    generate_system_requirements_list(summaries)
    print("\n[✓] Done!")

if __name__ == "__main__":
    main()