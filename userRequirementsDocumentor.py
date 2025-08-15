# Brief: Reads system requirement file and attempts to generate list of IEC 62304 compliant user requirements

import os
import requests
from pathlib import Path

# Configuration

# DeepMentor box
# LLM_API_URL = "http://192.168.2.163:8000/v1/chat/completions"  # OpenAI-compatible endpoint
# MODEL_NAME = "/app/models"                                     # Replace with your model name

# LM Studio
LLM_API_URL = "http://127.0.0.1:1234/v1/chat/completions"  # OpenAI-compatible endpoint
MODEL_NAME = "openai/gpt-oss-20b"                          # Replace with your model name

SYSTEM_REQUIREMENTS_FILE = "../output/deepseek-coder-v2/deviceSelection/systemRequirements.md"        # Replace with path of System Requirements file
USER_REQUIREMENTS_FILE = "../output/gpt-oss-20b/deviceSelection/userRequirements.md"                  # Replace with path of User Requirements file output 
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
    summary = summarize_file(SYSTEM_REQUIREMENTS_FILE)
    all_summaries.append(f"{summary}")

    return all_summaries

def generate_user_requirements_list(summaries: list):
    prompt = f"""
        You are analyzing a list of system requirements to understand the user requirements from which they were derived from.
        Your task is to consolidate the list into a condensed version so that each item sufficiently encapsulates the behaviour expected from the system requirements.
        Follow the rules below and return a list using markdown formatting and the accompanying template.

        Rules
        - Be concise. 
        - Limit to 1 to 3 requirements ensuring they collectively encapsulate all system requirement summaries
        - Describe how the behaviour can be adequately explained to anybody involved in the project from end user to developer

        Template
        ## User Requirements
        - The software shall <functional capability or behavior>.

        Here are the file summaries:
        {summaries}""" # Truncate if needed
    
    summary = call_llm(prompt)
    
    with open(USER_REQUIREMENTS_FILE, "w", encoding="utf-8") as file:
        file.write(summary)

    print(f"\n[✓] User requirements summary written to: {USER_REQUIREMENTS_FILE}")

def main():
    print("[*] Collecting summaries...\n")
    summaries = collect_all_summaries()
    print("\n[*] Generating user requirements overview...\n")
    generate_user_requirements_list(summaries)
    print("\n[✓] Done!")

if __name__ == "__main__":
    main()