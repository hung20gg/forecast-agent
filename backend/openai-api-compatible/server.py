import asyncio
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import yaml
import uuid
import time
import json
from env_config import load_env_config, get_env

# Load environment configuration
load_env_config()

# Add agent path to sys.path
agent_path = Path(__file__).parent.parent.parent / "agent"
sys.path.insert(0, str(agent_path))

from strategy import get_agent_state, get_agent, get_agent_config

# Load configuration
config_path = Path(__file__).parent / "config.yml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

app = FastAPI(title="OpenAI-Compatible Agent API", version="1.0.0")

# OpenAI API Models
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = int(time.time())
    owned_by: str = "agent-system"

class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage

def parse_model_name(model: str) -> tuple[Optional[str], str]:
    """Parse model name into strategy and base model.
    
    Examples:
        'react:gpt-4' -> ('react', 'gpt-4')
        'gpt-4' -> (None, 'gpt-4')
        'open-deep-research:claude-3-5-sonnet' -> ('open-deep-research', 'claude-3-5-sonnet')
    """
    if ':' in model:
        strategy, base_model = model.split(':', 1)
        return strategy, base_model
    return None, model

def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API key if configured."""
    configured_key = config['server'].get('api_key')
    if configured_key is None:
        return True
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    # Expected format: "Bearer sk-..."
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    provided_key = authorization.replace("Bearer ", "")
    if provided_key != configured_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True

@app.get("/v1/models")
async def list_models(authorization: Optional[str] = Header(None)) -> ModelListResponse:
    """List available models."""
    verify_api_key(authorization)
    
    models = []
    default_models = config.get('default_models', ['gpt-4.1-mini'])
    
    # Add strategy-based models
    for strategy_name, strategy_config in config['models'].items():
        for base_model in default_models:
            model_id = f"{strategy_name}:{base_model}"
            models.append(ModelInfo(
                id=model_id,
                owned_by=f"agent-{strategy_name}"
            ))
    
    # Add base models
    for base_model in default_models:
        models.append(ModelInfo(
            id=base_model,
            owned_by="openai"
        ))
    
    return ModelListResponse(data=models)

@app.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    authorization: Optional[str] = Header(None)
):
    """Create a chat completion."""
    verify_api_key(authorization)
    
    # Parse model name
    strategy, base_model = parse_model_name(request.model)
    
    # Validate strategy if specified
    if strategy and strategy not in config['models']:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown strategy: {strategy}. Available: {list(config['models'].keys())}"
        )
    
    # Prepare agent configuration
    agent_config = {
        "model_name": base_model,
        "streaming": request.stream
    }
    
    if strategy:
        agent_config["agent_type"] = strategy
        state_config = {"agent_type": strategy}
    else:
        # Default to react if no strategy specified
        agent_config["agent_type"] = "react"
        state_config = {"agent_type": "react"}
    
    # Create agent state and add messages (excluding system messages from user)
    state = get_agent_state(**state_config)
    agent_config = get_agent_config(**agent_config)
    
    # Add user messages (filter out system messages from request)
    for msg in request.messages[:-1]:
        if msg.role != "system":  # Skip user-provided system messages
            state.messages.append({
                "role": msg.role,
                "content": msg.content
            })

    state.user_request = request.messages[-1].content  # Last message is user request
    
    # Create and initialize agent
    agent = get_agent(config=agent_config)
    await agent.initialize()
    
    if request.stream:
        return StreamingResponse(
            stream_completion(agent, state, request.model),
            media_type="text/event-stream"
        )
    else:
        return await complete_non_streaming(agent, state, request.model)

async def stream_completion(agent, state, model: str):
    """Stream completion chunks."""
    request_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    
    try:
        async for chunk in agent.stream(state, stream_mode="custom"):
            try:
                # Handle different chunk types
                chunk_type = chunk.get('type')
                
                if chunk_type == 'content':
                    # Content chunk - ensure content is a string
                    content = chunk.get('content', '')
                    if not isinstance(content, str):
                        content = str(content)
                    
                    # Content chunk
                    delta = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "content": content
                            },
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(delta)}\n\n"
                
                elif chunk_type == 'log':
                    # Log chunk (optional, could be filtered)
                    pass
            except Exception as chunk_error:
                # Log but continue streaming
                import traceback
                print(f"[ERROR] Error processing chunk: {chunk_error}")
                print(traceback.format_exc())
                continue
        
        # Send final chunk
        final_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Streaming error: {e}")
        print(traceback.format_exc())
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "internal_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"

async def complete_non_streaming(agent, state, model: str):
    """Complete without streaming."""
    request_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    
    try:
        result = await agent.ainvoke(state)
        
        # Extract final assistant message
        final_message = None
        for msg in reversed(result.messages):
            if msg.get('role') == 'assistant' and msg.get('content'):
                final_message = msg.get('content')
                break
        
        if final_message is None:
            final_message = "No response generated"
        
        return ChatCompletionResponse(
            id=request_id,
            created=created,
            model=model,
            choices=[
                Choice(
                    index=0,
                    message=Message(role="assistant", content=final_message),
                    finish_reason="stop"
                )
            ],
            usage=Usage(
                prompt_tokens=0,  # Would need to calculate
                completion_tokens=0,
                total_tokens=0
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    
    host = get_env('BACKEND_HOST') or config['server'].get('host', '0.0.0.0')
    port = int(get_env('BACKEND_PORT') or config['server'].get('port', 8000))
    
    print(f"Starting OpenAI-compatible API server on {host}:{port}")
    print(f"Available strategies: {list(config['models'].keys())}")
    
    uvicorn.run(app, host=host, port=port)
