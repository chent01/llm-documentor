# Brief: Evaluate code of each file to generate software design document, then gather and generate architectural design document.

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

ROOT_DIR = "../app/src/view/pageManagers/deviceSelection"       # Replace with directory of target files
SUMMARY_DIR = Path("../output/gpt-oss-20b/summaries")           # Replace with directory path of Software Design file summaries output 
ARCHITECTURE_FILE = "../output/gpt-oss-20b/architecture.md"     # Replace with path of Architecture Design file output 
IGNORED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".exe", ".bin", ".woff", ".ttf", ".pdf"}

# Ensure output directories exist
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

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

    prompt = f"""
        You are analyzing a source code file containing a software component from a JavaScript-based project to understand its software design.
        
        Filename: {file_path.name} 
        Be concise. Return your response in Markdown format, completing the below template.
        
        Template
        ## Software Architectural Level and Description
        - whether the software component is a software item or unit according to IEC 62304's categorisation
        - description of what the code in this file does

        ## Internal Interfaces
        - How it interfaces with between other software items or units
        - Inputs and outputs with emphasis on any available constructors, methods or functions

        ## External Interfaces
        - How it interfaces with any exported or public interfaces (functions, classes, APIs)
        - How it interfaces with any imports or dependencies it uses
        - Inputs and outputs
        
        Code (full content of the file):
        {content}"""
    
    return call_llm(prompt)

def write_summary(file_path: Path, summary_text: str):
    filename = f"{file_path.name}.md"
    out_path = SUMMARY_DIR / filename
    
    with open(out_path, "w", encoding="utf-8") as file:
        file.write(summary_text)

def collect_all_summaries() -> list:
    all_summaries = []
    for root, _, files in os.walk(ROOT_DIR):
        for filename in files:
            full_path = Path(root) / filename

            if not is_text_file(full_path):
                continue
            
            print(f"[+] Summarizing: {full_path}")
            summary = summarize_file(full_path)
            write_summary(full_path, summary)
            all_summaries.append(f"## {filename}\n\n{summary}\n")

    return all_summaries

def generate_architecture_summary(summaries: list):
    prompt = f"""
        You are reviewing the overall architecture of a codebase.
        Based on the following file summaries, describe how the project fits together structurally.

        Consider:
        - Major components/modules
        - How they interact
        - Overall responsibilities
        - Architecture patterns (e.g. MVC, layered, plugin-based)

        Use Markdown formatting.

        Here are the file summaries:
        {summaries}""" # Truncate if needed
    
    architecture_summary = call_llm(prompt)
    
    with open(ARCHITECTURE_FILE, "w", encoding="utf-8") as file:
        file.write(architecture_summary)

    print(f"\n[✓] Architecture summary written to: {ARCHITECTURE_FILE}")

def main():
    print("[*] Starting codebase summarization...\n")
    summaries = collect_all_summaries()
    print("\n[*] Generating architecture overview...\n")
    generate_architecture_summary(summaries)
    print("\n[✓] Done!")

if __name__ == "__main__":
    main()