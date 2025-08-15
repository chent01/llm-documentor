# Brief: Recursively evaluate code in target directory to generate component requirements for each file

import os
import requests
from pathlib import Path

# Configuration

# DeepMentor box
# LLM_API_URL = "http://192.168.2.163:8000/v1/chat/completions"  # OpenAI-compatible endpoint
# MODEL_NAME = "/app/models"                                     # Replace with your model name

# LM Studio // may need to enable CORS in server settings // developer > settings > enable CORS
LLM_API_URL = "http://127.0.0.1:1234/v1/chat/completions"  # OpenAI-compatible endpoint
MODEL_NAME = "openai/gpt-oss-20b"                          # Replace with your model name

ROOT_DIR = "../app/src/view/pageManagers/deviceSelection"                 # Replace with directory of target files
SUMMARY_DIR = Path("../output/gpt-oss-20b/deviceSelection/summaries")     # Replace with path of output files
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
        Context:
        You are analyzing a source code file containing a software component from a JavaScript-based project to understand the component requirements the software design was tailored to.
        
        Filename: {file_path.name}
        - Be concise. 
        - Use “shall” to indicate mandatory requirements.
        - Be specific and measurable (avoid vague words like “fast”, “user-friendly”, “easy”).
        - Keep one requirement per statement — split if needed.
        - Include conditions and constraints where relevant (e.g., timing, range, accuracy).
        - Use consistent terminology aligned with your glossary.
        - Return your response in Markdown format, completing the below template.
        
        Template
        ## Component Requirements
        - The <component/module name> shall <detailed function or behavior> [with performance criteria] [following specified protocols].

        Code (full content of the file):
        {content}"""

    return call_llm(prompt)

def write_summary(file_path: Path, summary_text: str):
    filename = f"{file_path.name}.md"
    out_path = SUMMARY_DIR / filename
    
    with open(out_path, "w", encoding="utf-8") as file:
        file.write(summary_text)

def collect_all_summaries() -> list:
    for root, _, files in os.walk(ROOT_DIR):
        for filename in files:
            full_path = Path(root) / filename

            if not is_text_file(full_path):
                continue
            
            print(f"[+] Summarizing: {full_path}")
            summary = summarize_file(full_path)
            write_summary(full_path, summary)

def main():
    print("[*] Evaluating codebase...\n")
    collect_all_summaries()
    print("\n[✓] Done!")

if __name__ == "__main__":
    main()