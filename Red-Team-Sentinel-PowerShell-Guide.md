# Red-Team Sentinel: PowerShell Setup & Usage Guide

This guide explains how to set up **Red-Team Sentinel** on Windows using
PowerShell and run the pipeline in its different modes.

------------------------------------------------------------------------

## 📥 Step 1: Set Up the Project (Run Once)

If you have just cloned your GitHub repository or are setting it up on a
new machine, run these commands in order.

``` powershell
# 1. Navigate to your project folder
cd C:\Red-Team-Sentinel

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Download your model from Hugging Face
hf download GuhanSenthil/qwen3-4b-abliterated qwen3-4b-abliterated-q4.gguf --local-dir .

# 4. Build the model in Ollama (using the Modelfile in the repo)
ollama create qwen3-4b-abliterated -f Modelfile-Qwen3-4B
```

**Note:** The pipeline also has an auto-build feature, but running this
command manually can help verify the model setup before running tests.

------------------------------------------------------------------------

## 🚀 Step 2: Run the Pipeline (Usage Modes)

Once setup is complete, you can run the pipeline in different modes.

### 🛡️ Mode 1: Safe Mode (No Execution)

Use this mode to generate and inspect code without executing it. This is
especially important when evaluating untrusted or potentially harmful
model output.

``` powershell
python pipeline.py --prompt "Write a Python function to reverse a string"
```

**What happens:** The model generates code, the pipeline checks its
syntax, displays the result, and exits without executing the generated
code.

### ⚡ Mode 2: Live Mode (Execute & Repair)

Use this mode only for trusted, benign coding tasks in a properly
isolated test environment.

``` powershell
python pipeline.py --prompt "Write a function to reverse a string" --testrun
```

**What happens:** The pipeline executes the generated code with a
10-second timeout. If the code fails the configured tests, it may send
the error information back to the model for repair.

**Important:** A subprocess timeout is not a security sandbox. Do not
run untrusted generated code directly on your host machine. Use a
disposable, isolated VM or a properly restricted container with no
sensitive files, credentials, or network access.

### 🧪 Mode 3: Live Mode with Custom Tests

Use this mode to test a specific algorithm with your own test file.

``` powershell
python pipeline.py --prompt "Write a function spiral_matrix(matrix) that returns elements in spiral order" --testrun --tests spiral_tests.py
```

**What happens:** The pipeline generates the requested function, runs
the tests in `spiral_tests.py`, and may attempt to repair the
implementation if tests fail.

### 🧠 Mode 4: Multi-Agent Audit

Use this mode to translate or optimize code and ask the six audit agents
to assess semantic equivalence against a reference implementation.

``` powershell
python pipeline.py --prompt "Optimize this code to be faster" --reference original_code.py --testrun
```

**What happens:** The pipeline generates an optimized version, runs the
configured tests, and starts the six-agent audit to compare the new
implementation with `original_code.py`. An Arbiter then synthesizes the
reports and test results into a final verdict.

------------------------------------------------------------------------

## 🛑 Step 3: Stop the Pipeline

If the pipeline hangs or you need to stop it, press:

``` text
Ctrl + C
```

------------------------------------------------------------------------

## Before Running

-   Confirm that Ollama is installed and running.
-   Confirm that the model name matches the model created in Ollama.
-   Confirm that `requirements.txt`, `pipeline.py`, and the required
    Modelfile exist in the project directory.
-   Confirm that custom test files are present at the paths supplied to
    `--tests`.
-   Start in Safe Mode and inspect generated code before considering any
    execution.
-   Treat all model-generated code as untrusted. A 10-second timeout
    alone does not prevent filesystem access, network access, process
    creation, or other harmful side effects.

## Project Links

-   GitHub: https://github.com/GuhanSenthil/Red-Team-Sentinel-Safe-Orchestration-of-Uncensored-LLMs
-   Hugging Face: https://huggingface.co/GuhanSenthil/qwen3-4b-abliterated
