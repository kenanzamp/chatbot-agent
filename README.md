# Autonomous Agent

A WebSocket-based autonomous agent with tools and skills architecture. Built with FastAPI (Python) backend and vanilla JavaScript frontend.

## Features

- **ReAct Loop**: Reasoning + Acting agent pattern for multi-step problem solving
- **Tools**: Direct function calls via JSON Schema (LLM invokes them directly)
- **Skills**: Knowledge modules (SKILL.md + scripts) that the agent reads and executes
- **Streaming**: Real-time streaming responses via WebSocket
- **Fault Tolerance**: Circuit breakers and retry logic for reliability
- **Modern UI**: Clean, responsive chat interface

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key

### Installation

1. Clone the repository:
```bash
cd aav2
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Set your API key:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your-api-key-here
```

### Running the Server

```bash
cd /path/to/aav2
python -m agent.main
```

The server will start at `http://localhost:8000`

### Using the Chat Interface

1. Open your browser to `http://localhost:8000`
2. The chat interface will automatically connect via WebSocket
3. Start chatting! Try these examples:
   - "What time is it?"
   - "Calculate 1024 divided by 16"
   - "What is 15% of 250?"
   - "Convert 100 km to miles"
   - "Find the average of [85, 92, 78, 96, 88]"

## Project Structure

```
aav2/
├── config/
│   ├── config.yaml          # Main configuration
│   └── prompts/
│       └── system_prompt.txt # Agent system prompt
├── skills/
│   └── calculator/           # Example skill
│       ├── SKILL.md          # Skill documentation
│       └── scripts/
│           └── calc.py       # Skill implementation
├── frontend/
│   ├── index.html            # Chat UI
│   ├── styles.css            # Styling
│   └── app.js                # WebSocket client
├── src/agent/
│   ├── config/               # Configuration system
│   ├── core/                 # Agent logic (ReAct loop)
│   ├── llm/                  # LLM abstraction layer
│   ├── tools/                # Tool system
│   ├── skills/               # Skill system
│   ├── resilience/           # Fault tolerance
│   └── transport/            # WebSocket server
└── tests/                    # Test files
```

## Architecture

### Tools vs Skills

**Tools** are direct function calls:
- Fast, single-step invocation
- LLM sees JSON Schema and calls directly
- Examples: `get_current_time`, custom functions

**Skills** are knowledge modules:
- Agent reads SKILL.md documentation first
- Executes commands via `execute_command` tool
- More flexible, supports complex multi-step workflows
- Example: `calculator` skill with multiple operations

### ReAct Loop

The agent follows the ReAct (Reasoning + Acting) pattern:
1. Receive user message
2. Reason about what to do
3. Take action (tool call or skill command)
4. Observe result
5. Repeat until task is complete or respond

### WebSocket Protocol

Messages are JSON with a `type` field:

**Client → Server:**
- `chat`: Send a message
- `ping`: Heartbeat
- `reset`: Clear conversation
- `switch_model`: Change LLM model

**Server → Client:**
- `connected`: Connection established
- `text_delta`: Streaming text
- `tool_start`: Tool execution started
- `tool_result`: Tool execution result
- `complete`: Response finished
- `error`: Error occurred

## Configuration

Edit `config/config.yaml` to customize:

```yaml
llm:
  provider: "anthropic"
  model: "claude-sonnet-4-5-20250929"
  max_tokens: 4096
  temperature: 0.7

agent:
  max_iterations: 15
  tool_timeout: 30

skills:
  base_path: "./skills"
  auto_discover: true
```

## Creating Custom Skills

1. Create a directory under `skills/`:
```bash
mkdir -p skills/my_skill/scripts
```

2. Create `SKILL.md` with frontmatter:
```markdown
---
name: my_skill
description: Description of what the skill does
---

# My Skill

Documentation with command examples...
```

3. Create executable script in `scripts/`:
```python
#!/usr/bin/env python3
import json
import sys

# Your implementation
result = {"output": "result"}
print(json.dumps(result))
```

4. Restart the server to discover the new skill

## API Endpoints

- `GET /` - Chat UI
- `GET /health` - Health check
- `GET /info` - Server information
- `WebSocket /chat` - Chat endpoint

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Code Style

```bash
ruff check src/
ruff format src/
```

## License

MIT
