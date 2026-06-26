# MCP Server, Agents, and Skills

BosesPH Toolkit exposes its core pipeline capabilities to AI agents and LLM assistants through several mechanisms:

1. **Model Context Protocol (MCP) Server**: Provides standardized tools, resources, and prompts for LLM clients.
2. **Dedicated Autonomous Agent**: A standalone script that runs reviews and triggers pipeline operations automatically.
3. **Custom Skill**: Instructions for agents (like Gemini in Antigravity IDE) to teach them how to use the pipeline.

---

## 1. MCP Server

The BosesPH MCP server lets AI assistants call pipeline tools directly. It wraps the core CLI/API logic into a FastMCP application.

### Installation & Usage

Install the MCP extras:

```bash
python -m pip install -e ".[mcp]"
```

Run the server (uses stdio transport by default):

```bash
bosesph-mcp
```

### Claude Desktop Configuration

To use the BosesPH tools in Claude Desktop, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bosesph": {
      "command": "/path/to/.venv/bin/bosesph-mcp",
      "env": {
        "BOSESPH_WORKSPACE": "/path/to/outputs"
      }
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|---|---|
| `get_project_status` | Dataset stats, WER/CER metrics, model status |
| `validate_metadata` | Validate a dataset's `metadata.csv` |
| `import_pld_session` | Import a PLD recording session |
| `normalize_transcripts` | Normalize transcript formatting |
| `apply_review_decision` | Apply a review decision (approved/rejected/needs_fix) to a single clip |
| `build_dataset` | Build dataset with train/val/test splits |
| `transcribe_audio` | Transcribe a single audio file |
| `transcribe_dataset` | Transcribe an entire dataset split |
| `evaluate_predictions` | Compute WER/CER from predictions |
| `get_dataset_stats` | Detailed dataset statistics |
| `list_dataset_clips` | List clips in a dataset split |

### Available Resources & Prompts

- **Resources**:
  - `bosesph://dataset/stats` — JSON dataset statistics
  - `bosesph://benchmark/report` — Latest Markdown benchmark report
- **Prompts**:
  - `full_pipeline` — Guides the LLM through the entire workflow (import to evaluation)
  - `evaluate_model` — Guides the LLM through benchmarking a specific ASR model

---

## 2. Dedicated BosesPH Agent

A standalone Python agent (`apps/agent/`) acts as an autonomous reviewer and orchestrator. It connects to the `bosesph-mcp` server locally and uses an LLM (via the Anthropic API) to automatically review pending transcripts based on the transcription guidelines, and trigger dataset builds and evaluations when thresholds are met.

### Running the Agent

The agent requires the MCP server to be accessible (usually in the same virtual environment).

```bash
# 1. Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 2. Install agent dependencies
python -m pip install -e "apps/agent"

# 3. Run the agent
python apps/agent/agent.py
```

The agent will execute an autonomous loop, listing reviewable clips, making decisions based on standard tagging rules, and moving the pipeline forward.

---

## 3. Custom Skill for AI Agents

The `.agents/skills/bosesph-pipeline/` directory contains a **Custom Skill** that teaches any AI agent how to operate the BosesPH pipeline. It includes:

- `SKILL.md` — full pipeline instructions, validation rules, transcript conventions, and CLI/MCP/API command mappings.
- `examples/quick_start.md` — a complete end-to-end workflow example.
- `references/metadata_format.md` — metadata CSV schema reference.
- `references/transcript_rules.md` — transcription tag and quality rules.

Agents that support the skill format (such as Gemini in Antigravity IDE) will automatically discover and load these instructions when working in this workspace. For other agents, the skill files can be manually included as context or system prompts to guide their behavior.
