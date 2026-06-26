# BosesPH Toolkit: Project Ideas & Hackathon Strategy

This document compiles the key findings, architectural extensions, and strategic positioning ideas discussed for the BosesPH Toolkit hackathon submission.

---

## 1. Expanding into the AI Agent Ecosystem
The modular architecture of the BosesPH Toolkit (CLI and pipeline steps) makes it perfectly suited for integration with modern AI agent workflows.

*   **MCP Server (Model Context Protocol):** 
    By wrapping the Python backend into an MCP server, the toolkit's capabilities can be exposed as standardized tools to LLMs (like Claude or Gemini).
    *   *Examples:* `transcribe_ph_audio`, `get_dataset_stats`, `run_asr_evaluation`.
*   **Custom Skills:** 
    We can create a "Skill" (instructions and context) that teaches a general-purpose agent how to use the BosesPH pipeline. This includes rules like validating metadata before building datasets, and understanding custom tags like `[noise]`.
*   **Dedicated BosesPH Agent:**
    A specialized agent that autonomously manages the speech pipeline. It could act as an autonomous reviewer for transcripts, continuously learn by triggering fine-tuning jobs when new audio thresholds are met, or scrape public domain video/audio to ingest into the pipeline automatically.

## 2. Bridging the Gap Between Sound and Meaning
A critical distinction in speech technology is understanding that **ASR (Automatic Speech Recognition) models do not understand meaning**.

*   **ASR's Role:** Fine-tuning an ASR model (like Whisper) strictly teaches it the mapping between acoustic sounds and text characters. It improves spelling and transcription accuracy but has zero comprehension of the words.
*   **The LLM Landscape for PH Languages:**
    *   *Tagalog:* Excellent understanding due to high online resource availability.
    *   *Cebuano/Ilocano:* Moderate understanding; occasionally hallucinates or mixes grammar.
    *   *Kapampangan, Hiligaynon, etc.:* Weak to poor. These are "Low-Resource Languages."
*   **The BosesPH Solution:** LLMs struggle with low-resource languages because they are primarily spoken, not written. BosesPH solves this by converting raw regional speech into high-quality, clean text transcripts, creating the datasets needed to train future LLMs.

## 3. Integrating Dictionary Embeddings for Meaning Extraction
To extract meaning from the Kapampangan transcripts, we can leverage external resources like the `keithmanaloto/kapampangan-dictionary-embeddings` dataset on Hugging Face.

*   **The RAG Approach (Retrieval-Augmented Generation):**
    Instead of relying on an LLM to guess Kapampangan translations, we can use the dictionary embeddings as a "cheat sheet".
    1.  *ASR Output:* "Makananu ku pumunta king palengki?"
    2.  *Retrieve:* Look up definitions in the embedding dataset (Makananu = How, pumunta = to go, palengki = market).
    3.  *Generate:* Feed the transcript AND the definitions to the LLM to construct a grammatically correct English translation.
*   **Direct Translation Pipeline:**
    Using the dictionary for direct word-for-word lookup, which provides literal meanings but may miss contextual grammar.

## 4. Hackathon Strategy: Aligning with the Case Study
The hackathon case study explicitly asks for **"foundational infrastructure... that future developers and researchers can extend,"** and specifically states that **"The focus is not on building applications."**

*   **The Trap:** Pitching an end-to-end translation chatbot or consumer web app.
*   **The Winning Frame:** Pitch the project as a **Reproducible Data Pipeline** and a **New Open Dataset**.
    *   *Enriching the Dataset:* Use the pipeline and dictionary embeddings to automatically append an `english_translation` column to the generated datasets. This provides researchers with a rich, multi-modal open resource.
    *   *Building an Inference Pipeline:* Open-source the API/MCP Server code that connects the acoustic model (ASR) with the semantic model (Dictionary Embeddings). This gives future developers the exact "foundational infrastructure" they need to build their own voice-driven technologies.
