# OpenAI-Compatible Agent API Server

An OpenAI API-compatible server that wraps agent strategies (ReAct, Deep Research, etc.) and exposes them via familiar OpenAI chat completion endpoints.

## Features

- **OpenAI API Compatible**: Works with any OpenAI client library
- **Multiple Strategies**: Support for different agent strategies via model names
- **Streaming Support**: SSE-based streaming responses
- **Configurable Models**: Define strategy-model mappings via YAML config
- **Authentication**: Optional API key authentication

## Installation

```bash
cd backend/openai-api-compatible
pip install -r requirements.txt
```

## Configuration

Edit `config.yml` to configure:

```yaml
models:
  react:
    strategy: "react"
    description: "ReAct agent strategy"
  
  open-deep-research:
    strategy: "open-deep-research"
    description: "Deep research strategy"

default_models:
  - "gpt-4.1-mini"
  - "gpt-4o"

server:
  host: "0.0.0.0"
  port: 8000
  api_key: null  # Set to require authentication
```

## Usage

### Starting the Server

```bash
python server.py
```

Or with uvicorn:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### Making Requests

#### Using OpenAI Python Client

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # Not required if api_key is null in config
)

# Use ReAct strategy with GPT-4
response = client.chat.completions.create(
    model="react:gpt-4.1-mini",
    messages=[
        {"role": "user", "content": "What is the stock price of VIC?"}
    ]
)

print(response.choices[0].message.content)
```

#### Streaming

```python
stream = client.chat.completions.create(
    model="react:gpt-4.1-mini",
    messages=[{"role": "user", "content": "Analyze VIC stock"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end='', flush=True)
```

#### Using cURL

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "react:gpt-4.1-mini",
    "messages": [
      {"role": "user", "content": "Get VIC stock price"}
    ]
  }'
```

## Model Naming Convention

Models follow the pattern: `<strategy>:<base_model>`

Examples:
- `react:gpt-4.1-mini` - ReAct strategy with GPT-4.1-mini
- `open-deep-research:gpt-4o` - Deep research strategy with GPT-4o
- `gpt-4.1-mini` - Direct model usage (defaults to ReAct)

## API Endpoints

### List Models
```
GET /v1/models
```

### Create Chat Completion
```
POST /v1/chat/completions
```

### Health Check
```
GET /health
```

## System Prompts

**Important**: User-provided system messages are automatically filtered out. Each agent strategy has its own internal system prompt that cannot be overridden via the API.

## Authentication

Set `api_key` in `config.yml` to enable authentication:

```yaml
server:
  api_key: "sk-your-secret-key"
```

Then include it in requests:
```python
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sk-your-secret-key"
)
```

## Integration Examples

Works with any OpenAI-compatible tool:

- **LangChain**: Use as a ChatOpenAI instance
- **LlamaIndex**: Configure as OpenAI endpoint
- **Continue.dev**: Add as custom model provider
- **Cursor**: Configure as OpenAI API endpoint

Example LangChain:
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    model="react:gpt-4.1-mini",
    api_key="dummy"
)

response = llm.invoke("What is VIC stock price?")
```

## Error Handling

The API returns standard OpenAI error formats:

```json
{
  "error": {
    "message": "Unknown strategy: invalid",
    "type": "invalid_request_error"
  }
}
```

## Development

To add new strategies:

1. Implement the strategy in `agent/strategy/`
2. Register it in `agent/strategy/__init__.py`
3. Add configuration to `config.yml`
4. Restart the server

## License

See main project LICENSE
