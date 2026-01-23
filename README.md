# Meeting Transcript Processor V8

A fact-first, hallucination-resistant meeting transcript processor that extracts action items, todos, and follow-up emails using LangGraph and LLMs.

## 🎯 Key Features

- **Fact-First Architecture**: Extracts facts once, validates them, then derives all outputs from validated facts only
- **No Hallucinations**: LLM never sees the original transcript during output generation - only validated facts
- **Hybrid Validation**: Rule-based (fast, free) + AI-based (quality checks) with retry logic
- **Multi-Provider Support**: OpenAI, Google Gemini, or Ollama (local)
- **Auditability**: Every output traces back to source facts with exact quotes

## 📋 Prerequisites

- Python 3.9+
- One of the following:
  - OpenAI API key (for GPT-4o)
  - Google API key (for Gemini)
  - Ollama installed locally (for qwen2.5 or other models)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd langgraph_meet_analyzer
```

### 2. Create Virtual Environment

#### macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows (Command Prompt):
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

#### Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

#### Option A: Using OpenAI (Recommended for Production)
```env
OPENAI_API_KEY=your_openai_api_key_here
```

#### Option B: Using Google Gemini
```env
GOOGLE_API_KEY=your_google_api_key_here
```

#### Option C: Using Ollama (Local, Free)
```env
OLLAMA_BASE_URL=http://localhost:11434
```

**Note**: If using Ollama, make sure it's installed and running:
```bash
# Install Ollama from https://ollama.ai
# Pull the model
ollama pull qwen2.5:latest
```

### 5. Configure the Model in run_v8.py

Edit `run_v8.py` to set your preferred provider and model:

```python
# For OpenAI (best quality, recommended)
result = process_meeting(
    transcription=transcript,
    provider=LLMProvider.OPENAI,
    model_name="gpt-4o"  # or "gpt-4o-mini" for cheaper
)

# For Google Gemini
result = process_meeting(
    transcription=transcript,
    provider=LLMProvider.GEMINI,
    model_name="gemini-1.5-pro"
)

# For Ollama (local, free, but lower quality)
result = process_meeting(
    transcription=transcript,
    provider=LLMProvider.OLLAMA,
    model_name="qwen2.5:latest"  # or "llama3.1", "mistral", etc.
)
```

## 📖 Usage

### Basic Usage

1. Place your meeting transcript in a text file (e.g., `transcript.txt`)

2. Run the processor:
```bash
python run_v8.py
```

3. Find the results in `results_v8/meeting_outputs.json`

### Custom Transcript

Edit `run_v8.py` to point to your transcript file:

```python
# Read transcript
with open("your_transcript.txt", "r") as f:
    transcript = f.read()
```

### Output Format

The processor generates:

```json
{
  "summary": "Concise 2-3 sentence summary",
  "action_points": [
    {
      "description": "Strategic high-level goal",
      "priority": "High|Medium|Low",
      "source_facts": ["fact 1", "fact 2"]
    }
  ],
  "todos": [
    {
      "task": "Specific actionable task",
      "deadline": "Friday morning" or null,
      "priority": "High|Medium|Low",
      "source_facts": ["fact 1"]
    }
  ],
  "follow_up_emails": [
    {
      "subject": "Meeting Follow-Up",
      "body": "Professional email text",
      "source_facts": ["fact 1", "fact 2"]
    }
  ],
  "metadata": {
    "total_facts_extracted": 20,
    "total_facts_validated": 19,
    "facts_discarded": 1
  }
}
```

## 🏗️ Architecture

### Fact-First Pipeline

```
1. Normalize Transcript
   ↓
2. Extract Facts (4 separate calls)
   - Decisions
   - Action Items
   - Deadlines
   - Metrics
   ↓
3. Validate Facts (rule-based)
   ↓
4. Generate Outputs (from facts only)
   - Summary
   - Action Points
   - Todos
   - Email
   ↓
5. Compliance Check
```

### Key Principles

1. **Single Source of Truth**: Facts are extracted once and validated once
2. **No Re-interpretation**: Output generation never sees the original transcript
3. **Validation with Feedback**: Failed outputs retry with specific feedback
4. **Skip Conditionals**: Ignores "if/might/may" statements (not commitments)

## 🔧 Configuration

### Adjusting Retry Logic

Edit generation nodes in `src2/nodes/` to change retry attempts:

```python
max_retries = 3  # Change to 2 or 5 as needed
```

### Adjusting Validation Strictness

Edit `src2/nodes/validate_outputs.py` to change validation thresholds:

```python
if rule_score < 8:  # Change to 7 for more lenient, 9 for stricter
```

## 📁 Project Structure

```
langgraph_meet_analyzer/
├── src2/                      # V8 Fact-First Architecture
│   ├── nodes/                 # LangGraph nodes
│   │   ├── normalize.py       # Transcript cleaning
│   │   ├── extract_facts.py   # Fact extraction (4 calls)
│   │   ├── validate_facts.py  # Rule-based validation
│   │   ├── generate_summary.py
│   │   ├── generate_action_points.py
│   │   ├── generate_todos.py
│   │   ├── generate_email.py
│   │   ├── validate_outputs.py # Output validation
│   │   └── compliance_check.py
│   ├── models.py              # Pydantic models
│   ├── graph.py               # LangGraph workflow
│   ├── processor.py           # Main interface
│   └── llm_provider.py        # LLM initialization
├── run_v8.py                  # Main entry point
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
└── README.md                  # This file
```

## 🐛 Troubleshooting

### "No module named 'langchain_openai'"
```bash
pip install -r requirements.txt
```

### "OPENAI_API_KEY not found"
Make sure `.env` file exists and contains your API key.

### Ollama connection error
```bash
# Check if Ollama is running
ollama list

# Start Ollama if needed
ollama serve
```

### Poor quality outputs with Ollama
Ollama models (especially smaller ones like qwen2.5) produce lower quality than GPT-4o. For production use, we recommend OpenAI GPT-4o.

### "Not specified" appearing in deadlines
This is a known issue with smaller models. The validation should catch and retry, but if it persists, switch to GPT-4o.

## 🎯 Best Practices

1. **Use GPT-4o for production** - Best quality, most reliable
2. **Use Ollama for development** - Free, fast, good for testing
3. **Keep transcripts clean** - Remove filler words, fix obvious typos
4. **Review outputs** - Always verify critical information
5. **Check source_facts** - Trace outputs back to original facts for auditability

## 📊 Performance

- **GPT-4o**: ~60 seconds, excellent quality, ~$0.50 per transcript
- **Gemini 1.5 Pro**: ~45 seconds, good quality, ~$0.30 per transcript
- **Ollama qwen2.5**: ~90 seconds, acceptable quality, free (local)

## 🤝 Contributing

This is a personal project, but suggestions are welcome! Open an issue or submit a pull request.

## 📄 License

MIT License - feel free to use and modify as needed.

## 🙏 Acknowledgments

Built with:
- [LangChain](https://langchain.com/) - LLM framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Workflow orchestration
- [Pydantic](https://pydantic.dev/) - Data validation

---

**Note**: This is V8 (Fact-First Architecture). Previous versions (V1-V7) are in `/versions_processor` for reference but are not maintained.
