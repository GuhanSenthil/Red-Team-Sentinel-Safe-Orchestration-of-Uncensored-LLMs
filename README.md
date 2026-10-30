# Red-Team-Sentinel-Safe-Orchestration-of-Uncensored-LLMs
# Qwen3-4B Abliterated & Secure Validation Pipeline

## ⚠️ IMPORTANT DISCLAIMER & CYBERSECURITY WARNING
This repository contains research on **Abliteration** (the mathematical removal of safety alignment from LLMs) and a pipeline that **executes AI-generated code**. 

*   **FOR RESEARCH ONLY:** This is strictly for educational, red-teaming, and AI safety research purposes. Do not use in production.
*   **UNCENSORED MODEL:** The model has no safety guardrails. It **will** generate malicious code (malware, phishing, exploits) and comply with harmful prompts.
*   **EXECUTION RISK:** The pipeline executes LLM-generated Python code. While we use subprocess isolation, timeouts, and default-safe modes, executing untrusted AI code is inherently dangerous. We are not responsible for any damage caused. **Always run this in a sandboxed VM or Docker container.**

