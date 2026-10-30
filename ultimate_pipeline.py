#!/usr/bin/env python3
"""
ULTIMATE RESEARCH PIPELINE (v9 - Robust Context & Sanitization)
"""

import argparse
import asyncio
import ast
import os
import re
import subprocess
import sys
import tempfile
import time
import ollama

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3-4b-abliterated"
MODELFILE_PATH = "Modelfile-Qwen3-4B"
RUN_TIMEOUT = 10
MAX_ITERATIONS = 3

client = ollama.Client(host=OLLAMA_HOST)

# ==========================================
# 🧠 MODEL MANAGER
# ==========================================
def log(tag, message):
    print(f"[{tag}] {message}", flush=True)

def banner(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}", flush=True)

def ensure_ollama_running():
    log("SYSTEM", "Checking Ollama server status...")
    try:
        client.list()
        log("SYSTEM", "Ollama is already running.")
        return True
    except Exception:
        log("SYSTEM", "Ollama is not running. Starting server in background...")
        if sys.platform == "win32":
            subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        for _ in range(15):
            time.sleep(1)
            try:
                client.list()
                log("SYSTEM", "Ollama server started successfully.")
                return True
            except Exception:
                continue
        log("ERROR", "Failed to start Ollama. Please run 'ollama serve' manually.")
        return False

def ensure_model_exists():
    try:
        response = client.list()
        model_list = getattr(response, 'models', response.get('models', [])) if isinstance(response, dict) or hasattr(response, 'models') else response
        model_names = []
        for m in model_list:
            if isinstance(m, dict):
                model_names.append(m.get('name', m.get('model', '')))
            else:
                model_names.append(getattr(m, 'name', getattr(m, 'model', str(m))))
        
        if any(DEFAULT_MODEL in str(name) for name in model_names):
            log("SYSTEM", f"Model '{DEFAULT_MODEL}' is ready.")
            return True
            
        log("SYSTEM", f"Model '{DEFAULT_MODEL}' not found. Building from Modelfile...")
        if not os.path.exists(MODELFILE_PATH):
            log("ERROR", f"Modelfile not found at {MODELFILE_PATH}.")
            return False
            
        result = subprocess.run(["ollama", "create", DEFAULT_MODEL, "-f", MODELFILE_PATH], capture_output=True, text=True)
        if result.returncode == 0:
            log("SYSTEM", f"Model '{DEFAULT_MODEL}' created successfully.")
            return True
        else:
            log("ERROR", f"Failed to create model: {result.stderr}")
            return False
    except Exception as e:
        log("ERROR", f"Error checking model: {e}")
        return False

# ==========================================
# 🛠️ UTILITIES
# ==========================================
def clean_generated_code(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<think>.*\Z", "", text, flags=re.DOTALL | re.IGNORECASE)
    
    match = re.search(r"```(?:python|py)?[ \t]*\n(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    else:
        text = re.sub(r"^\s*```(?:python|py)?[ \t]*\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n?```\s*$", "", text)

    lines = text.split('\n')
    cleaned_lines = []
    in_test_block = False
    for line in lines:
        if line.strip().startswith("assert ") or line.strip().startswith("if __name__ =="):
            in_test_block = True
        if not in_test_block:
            cleaned_lines.append(line)
            
    return "\n".join(cleaned_lines).strip()

def check_syntax(code):
    if not code.strip(): return False, "Empty code."
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError on line {e.lineno}: {e.msg}"

def run_tests_in_subprocess(code, test_harness):
    with tempfile.TemporaryDirectory() as tmp:
        file_path = os.path.join(tmp, "solution.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code + "\n\n" + test_harness)

        try:
            proc = subprocess.run(
                [sys.executable, "-B", file_path],
                capture_output=True, text=True, timeout=RUN_TIMEOUT,
                stdin=subprocess.DEVNULL 
            )
            if proc.returncode == 0:
                return True, "All logic tests passed."
            
            raw_err = (proc.stderr or proc.stdout).strip()
            error_lines = raw_err.split('\n')
            clean_lines = [line for line in error_lines if not line.strip().startswith("assert ")]
            clean_err = "\n".join(clean_lines)[-1500:]
            
            return False, clean_err
        except subprocess.TimeoutExpired:
            return False, f"TimeoutError: Execution exceeded {RUN_TIMEOUT}s."

# ==========================================
# 🔄 PIPELINE PHASE 1
# ==========================================
async def phase1_generate_repair(prompt, test_harness, testrun, model, max_iters):
    banner("PHASE 1: GENERATE -> VALIDATE -> REPAIR LOOP")
    current_prompt = f"Write Python code for: {prompt}\nOutput ONLY the code."
    
    system_prompt = (
        "You are an expert Python developer. "
        "Output ONLY valid, runnable Python code. "
        "DO NOT include any markdown formatting, test cases (asserts), or explanations."
    )

    for i in range(1, max_iters + 1):
        log(f"ITER {i}", "Generating code...")
        
        res = await asyncio.to_thread(
            client.chat, 
            model=model, 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": current_prompt}
            ],
            options={"num_ctx": 8192}
        )
        code = clean_generated_code(res["message"]["content"])

        log("VALIDATE", "Checking syntax (ast.parse)...")
        syntax_ok, syntax_err = check_syntax(code)

        if not syntax_ok:
            log("FAIL", f"Syntax Error: {syntax_err}")
            current_prompt = f"Your code failed syntax check:\n{syntax_err}\nFix this code:\n{code}\nOutput ONLY the fixed code."
            continue

        if not testrun:
            log("SKIP", "Syntax is valid. Execution skipped (Safe Mode).")
            print("\n--- GENERATED CODE (NOT EXECUTED) ---\n" + code + "\n----------------------")
            return code, False

        log("VALIDATE", "Running runtime and logic tests...")
        logic_ok, logic_err = run_tests_in_subprocess(code, test_harness)

        if logic_ok:
            log("SUCCESS", f"Code passed all validations on iteration {i}!")
            print("\n--- VALIDATED CODE ---\n" + code + "\n----------------------")
            return code, True
        else:
            log("FAIL", f"Logic/Runtime Error:\n{logic_err}")
            current_prompt = f"Your code failed the hidden tests. Do NOT write test cases. Fix the function so it passes.\nError:\n{logic_err}\nFix this code:\n{code}\nOutput ONLY the fixed code."

    log("ERROR", "Max iterations reached. Returning last attempt.")
    return code, False

# ==========================================
# 🧠 PIPELINE PHASE 2
# ==========================================
REPORT_FORMAT = "End with 'VERDICT: MATCH' or 'VERDICT: MISMATCH' followed by a reason."
ANALYZER_PROMPTS = {
    "control_flow": "Compare control flow (loops, branches). " + REPORT_FORMAT,
    "data_flow": "Compare data flow (types, mutations). " + REPORT_FORMAT,
    "io": "Compare input/output and side effects. " + REPORT_FORMAT,
    "library_api": "Compare libraries and APIs used. " + REPORT_FORMAT,
    "exception": "Compare error handling and edge cases. " + REPORT_FORMAT,
    "specification": "Does the target satisfy the source's intended spec? " + REPORT_FORMAT
}
ARBITER_PROMPT = (
    "You are the final arbiter. Review the source, target, analyzer reports, and test results. "
    "Conclude with 'FINAL VERDICT: EQUIVALENT' or 'FINAL VERDICT: INEQUIVALENT'."
)

async def call_llm(system_prompt, user_content, model):
    try:
        res = await asyncio.to_thread(
            client.chat, model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
            options={"num_ctx": 8192}
        )
        return clean_generated_code(res["message"]["content"])
    except Exception as e:
        return f"ERROR: {e}"

async def phase2_semantic_audit(source_code, target_code, test_passed, model):
    banner("PHASE 2: MATCHFIX MULTI-AGENT SEMANTIC AUDIT")
    user_content = f"SOURCE:\n```python\n{source_code}\n```\n\nTARGET:\n```python\n{target_code}\n```"

    log("ANALYZERS", "Running 6 parallel agents...")
    tasks = [call_llm(prompt, user_content, model) for prompt in ANALYZER_PROMPTS.values()]
    reports = await asyncio.gather(*tasks)

    for name, report in zip(ANALYZER_PROMPTS.keys(), reports):
        print(f"\n--- [{name.upper()}] ---\n{report}")

    log("ARBITER", "Synthesizing final verdict...")
    test_summary = "PASSED" if test_passed else "NOT RUN (or FAILED)"
    
    combined_reports = "\n\n".join(reports)
    if len(combined_reports) > 4000:
        combined_reports = combined_reports[:4000] + "\n...[TRUNCATED FOR CONTEXT]..."

    arb_content = (
        f"SOURCE:\n{source_code}\n\n"
        f"TARGET:\n{target_code}\n\n"
        f"REPORTS:\n{combined_reports}\n\n"
        f"TEST RESULTS ON TARGET: {test_summary}"
    )
    arbiter_verdict = await call_llm(ARBITER_PROMPT, arb_content, model)
    print(f"\n--- [ARBITER VERDICT] ---\n{arbiter_verdict}")

# ==========================================
# 🚀 MAIN EXECUTION
# ==========================================
DEFAULT_PROMPT = "Write a function `calculate_stats(nums)` that returns a tuple (min, max, average). Handle empty lists by returning None."
DEFAULT_TEST_HARNESS = """
assert calculate_stats([1, 2, 3, 4, 5]) == (1, 5, 3.0), "Failed standard list"
assert calculate_stats([]) is None, "Failed empty list"
print("All tests passed!")
"""

def parse_args():
    p = argparse.ArgumentParser(description="Self-contained AI Pipeline (Model + Validation)")
    p.add_argument("--prompt", default=DEFAULT_PROMPT, help="What to generate.")
    p.add_argument("--tests", help="Path to custom test asserts.")
    p.add_argument("--reference", help="Path to reference code for semantic audit.")
    p.add_argument("--model", default=DEFAULT_MODEL, help="Model tag.")
    p.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS, help="Max repair attempts.")
    p.add_argument("--testrun", action="store_true", help="ACTUALLY EXECUTE the code. If omitted, runs in Safe Mode.")
    return p.parse_args()

async def main():
    args = parse_args()

    if not ensure_ollama_running(): return
    if not ensure_model_exists(): return

    prompt = args.prompt
    
    if args.tests:
        if not os.path.exists(args.tests):
            log("ERROR", f"Test file not found: '{args.tests}'.")
            return
        test_harness = open(args.tests, "r", encoding="utf-8").read()
    else:
        test_harness = DEFAULT_TEST_HARNESS

    reference_code = None
    if args.reference:
        if not os.path.exists(args.reference):
            log("ERROR", f"Reference file not found: '{args.reference}'.")
            return
        reference_code = open(args.reference, "r", encoding="utf-8").read()

    if args.testrun:
        log("MODE", "LIVE EXECUTION ENABLED (--testrun). Code will be executed.")
    else:
        log("MODE", "SAFE MODE ENABLED. Code will NOT be executed.")

    try:
        validated_code, tests_passed = await phase1_generate_repair(
            prompt, test_harness, args.testrun, args.model, args.max_iterations
        )
    except Exception as e:
        print(f"Connection Error: {e}")
        return

    if validated_code:
        if reference_code:
            await phase2_semantic_audit(reference_code, validated_code, tests_passed, args.model)
        else:
            log("AUDIT", "Skipping Phase 2 (MatchFix Audit) because no --reference file was provided.")

if __name__ == "__main__":
    asyncio.run(main())
