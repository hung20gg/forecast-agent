import os
from llm import get_llm_wrapper
from core.mcp_client import MCPClient
from core.state import AgentState
import wandb
import weave
from uuid import uuid4
from typing import Optional
from langgraph.graph import StateGraph
from langgraph.config import get_stream_writer
import json
from typing import List, Dict, Any, AsyncIterable, Annotated, TypeVar, Generic
from pydantic import BaseModel, Field
from datetime import datetime
from dotenv import load_dotenv
import asyncio


load_dotenv()

from .logger import logger

WANDB_API_KEY = os.getenv("WANDB_API_KEY")
WANDB_NAME = os.getenv("WANDB_NAME", "neu-solution/kltn")
wandb.login(key=WANDB_API_KEY)
weave.init(WANDB_NAME)
class BaseAgentMCPConfig(BaseModel):
    agent_type: str = "base"
    model_name: str
    urls: Optional[List[str]] = None
    streaming: bool = False
    message_saver: Optional[str] = None
    current_time : Annotated[str, "The current date and time in ISO 8601 format"] = Field(
        default_factory=lambda: datetime.now().isoformat()
    )
    
StateT = TypeVar("StateT", bound=AgentState)
ConfigT = TypeVar("ConfigT", bound=BaseAgentMCPConfig)

class BaseAgentMCP(Generic[StateT, ConfigT]):
    def __init__(self, config: ConfigT) -> None:
        self.config = config
        self.llm = get_llm_wrapper(config.model_name)
        self.mcp_client = MCPClient(config.urls)
        self._initialized = False
        self.graph = self.build_graph()
        self.streaming = config.streaming
        self.session_id = str(uuid4())


        if config.message_saver == 'mongodb':
            from llm.llm_logger.log_mongodb import LLMLogMongoDB
            self.llm = LLMLogMongoDB(llm=self.llm)
     
        elif config.message_saver == 'postgres':
            from llm.llm_logger.log_postgres import LLMLogPostgres
            self.llm = LLMLogPostgres(llm=self.llm)
            

    async def initialize(self) -> None:
        """Initialize async components"""
        if not self._initialized:
            await self.mcp_client.initialize()
            self._initialized = True

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass


    def is_tool_calling_finished(self, state: StateT) -> str:
        if len(state.messages[-1].get("tool_calls", [])) == 0:
            return 'end'
        return 'continue'
    
    async def _single_tool_execute(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        
        tool_id = None
        tool_response = None
        
        try:
            tool_id = tool_call.get("id")
            function = tool_call.get("function", {})
            function_name = function.get("name")
            logger.info(f"[FUNCTION]: {function_name} {function.get('arguments')}")
            arguments = json.loads(function.get("arguments"))

            tool_result = await self.mcp_client.call_tool(function_name, arguments)
            
            #post-process tool result
            response = tool_result.content[0].text
            if response.startswith('{') or response.startswith('['):
                try:
                    response = json.loads(response)
                except json.JSONDecodeError:
                    pass  # Keep original text if JSON parsing fails

            tool_response = json.dumps(response, ensure_ascii=False)
        
        except Exception as e:          
            logger.error(f"Error executing tool: {e}")
            tool_response = f"Error executing tool: {e}"
        
        return {
            "role": "tool",
            "tool_call_id": tool_id,
            "content": tool_response
        }
    
    async def _tool_execute(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tool_responses = []
        tool_responses = await asyncio.gather(*[
            self._single_tool_execute(tool_call) for tool_call in tool_calls
        ])

        return tool_responses


    @weave.op(call_display_name="Tool Execute")
    async def tool_execute(self, state: StateT) -> StateT:

        tool_messages = await self._tool_execute(state.messages[-1].get("tool_calls", []))
        state.messages.extend(tool_messages)
        return state
    

    async def _tool_calling(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:

        content = ""
        tool_calls = []
        
        if not self.streaming:
            tool_responses = await self.llm.tool_calling_async(messages=messages, tools = tools)
            if isinstance(tool_responses, dict):
                content = tool_responses.get('content')
                tool_calls = tool_responses.get('tool_calls')
        else:
            # Get stream writer inside the graph execution context
            stream_writer = get_stream_writer()
            


            async for chunk in self.llm.stream_tool_calling_async(messages, tools = tools):
                if isinstance(chunk, dict) and chunk.get('type') == 'content':
                    content += chunk.get('content', '')
                    stream_writer({'type': 'content', 'content': chunk.get('content', '')})

                elif isinstance(chunk, dict) and chunk.get('type') == 'function':
                    tool_calls.append(chunk)
                    stream_writer({'type': 'log', 'log': 'Identified tool call: ' + str(chunk) + '\n'})

        return {
            'content': content,
            'tool_calls': tool_calls
        }


    @weave.op(call_display_name="Tool Calling")
    async def tool_calling(self, state: StateT) -> StateT:

        tool_calling_result = await self._tool_calling(messages=state.messages, tools=self.mcp_client.tools)
        state.messages.append({
            'role': "assistant",
            "content": tool_calling_result.get("content"),
            "tool_calls": tool_calling_result.get("tool_calls")
        })

        return state
    

    @weave.op(call_display_name="Finalize Agent State")
    async def finalize(self, state: StateT) -> StateT:
        if self.streaming:
            stream_writer = get_stream_writer()
            stream_writer({'type': 'state', 'state': state})
        return state

            
    def build_graph(self) -> Optional[StateGraph]:
        return None

    @weave.op(call_display_name="Invoke Agent")
    async def ainvoke(self, state: StateT) -> StateT:

        if not self.graph:
            raise ValueError("Workflow graph is not defined.")
        
        # Run the workflow
        with weave.thread(self.session_id) as thread_ctx:
            with weave.attributes({'type': 'non-stream', 'Agent': self.config.agent_type}):
                logger.info(f"Starting agent invocation with thread ID: {self.session_id}")
                result  = await self.graph.ainvoke(state)
                if result is None:
                    raise ValueError("Workflow execution returned None.")

        return type(state)(**result)

    @weave.op(call_display_name="Stream Agent")
    async def stream(self, state: StateT, stream_mode="custom") -> AsyncIterable[Dict[str, Any]]:
        
        if not self.graph:
            raise ValueError("Workflow graph is not defined.")
       
        with weave.thread(self.session_id) as thread_ctx:
            with weave.attributes({'type': 'stream', 'Agent': self.config.agent_type}):
                logger.info(f"Starting agent invocation with thread ID: {self.session_id}")
                
                async for chunk in self.graph.astream(state, stream_mode=stream_mode):
                    yield chunk
        

