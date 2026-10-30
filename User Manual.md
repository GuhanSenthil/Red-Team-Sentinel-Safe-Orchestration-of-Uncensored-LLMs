---

## 📖 User Manual: How to Use This Project

### Step 1: Prerequisites
1. Install [Ollama](https://ollama.com/) for your operating system.
2. Install the required Python package:
   ```bash
   pip install ollama

Step 2: Download and Build the Model
You can pull the pre-abliterated model directly from Hugging Face and build it in Ollama using the provided Modelfile-Qwen3-4B.

Download the GGUF file from Hugging Face:

bash
hf download GuhanSenthil/qwen3-4b-abliterated qwen3-4b-abliterated-q4.gguf --local-dir .
Build the model in Ollama using the Modelfile included in this repo:

bash
ollama create qwen3-4b-abliterated -f Modelfile-Qwen3-4B
Step 3: Run the Pipeline
The ultimate_pipeline.py script has a built-in safety mechanism. By default, it runs in Safe Mode, meaning it will only generate code and check the syntax, but it will not execute it.

Option A: Safe Mode (Default)
Generates code and checks syntax, but does NOT run it. Perfect for testing malicious prompts safely.

bash
python ultimate_pipeline.py --prompt "Write a Python script that reverses a string"
Option B: Live Execution Mode
Generates code, checks syntax, and executes the code in a safe subprocess with a 10-second timeout to validate the logic.

bash
python ultimate_pipeline.py --prompt "Write a Sudoku solver" --testrun
Option C: Using a Custom Test File
You can pass a Python file containing assert statements to test the logic of the generated code.

bash
python ultimate_pipeline.py --prompt "Write a function to add numbers" --testrun --tests my_tests.py
🛡️ Built-in Security Features
Because the abliterated model generates dangerous code, this pipeline was engineered with security in mind:

Opt-in Execution: Code is never run unless the --testrun flag is explicitly provided.

Timeout Enforcement: A hard 10-second timeout prevents infinite loops from freezing your machine.

Input Blocking: stdin=subprocess.DEVNULL is passed to the subprocess. If the generated code tries to ask for a password or user input, it instantly crashes instead of hanging.

Traceback Truncation: Error logs are limited to 1500 characters to prevent context-window exhaustion attacks.

📊 Model Details
Base Model: Qwen/Qwen3-4B-Instruct-2507

Abliteration: Heretic v1.4.0 (Difference-in-Means)

Quantization: Q4_K_M (GGUF)

KL Divergence: 0.0460 (Very low capability loss)

text

---

### 📄 2. `Modelfile-Qwen3-4B` (Copy and Paste this)
This file tells Ollama exactly how to load your model, including the correct ChatML template and stop tokens (which prevents the `@@@@@` loop you experienced earlier).

```dockerfile
# Point to the Hugging Face URL OR your local file path
FROM https://huggingface.co/GuhanSenthil/qwen3-4b-abliterated/resolve/main/qwen3-4b-abliterated-q4.gguf

TEMPLATE """<|im_start|>system
{{ if .System }}{{ .System }}{{ else }}You are a helpful assistant.{{ end }}<|im_end|>
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 2048
