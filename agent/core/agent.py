from llm import get_llm_wrapper
from core.mcp_client import MCPClient
from core.state import AgentState

from typing import Optional
from langgraph.graph import StateGraph
from langgraph.config import get_stream_writer
import json
from typing import List, Dict, Any, AsyncIterable
from pydantic import BaseModel
class BaseAgentMCPConfig(BaseModel):
    model_name: str
    urls: Optional[List[str]] = None
    streaming: bool = False
    message_saver: Optional[str] = None

class BaseAgentMCP:
    def __init__(self, config: BaseAgentMCPConfig) -> None:
        self.config = config
        self.llm = get_llm_wrapper(config.model_name)
        self.mcp_client = MCPClient(config.urls)
        self._initialized = False
        self.graph = self.build_graph()
        self.streaming = config.streaming


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


    def is_finished(self, state: AgentState) -> str:
        if len(state.messages[-1].get("tool_calls", [])) == 0:
            return 'end'
        return 'continue'


    async def tool_execute(self, state: AgentState) -> AgentState:

        tool_messages = []
        for tool_response in state.messages[-1].get("tool_calls", []):
            print('Executing tool call:', tool_response)
            tool_id = tool_response.get("id")
            function = tool_response.get("function")
            function_name = function.get("name")
            arguments = json.loads(function.get("arguments"))

            tool_result = await self.mcp_client.call_tool(function_name, arguments)
            
            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": json.dumps(tool_result.content[0].text)
            })

        state.messages.extend(tool_messages)
        return state
    

    async def tool_calling(self, state: AgentState) -> AgentState:

        if not self.streaming:
            tool_responses = await self.llm.tool_calling_async(messages=state.messages, tools = self.mcp_client.tools)
            content = tool_responses.get('content')
            tool_calls = tool_responses.get('tool_calls')
        else:
            # Get stream writer inside the graph execution context
            stream_writer = get_stream_writer()
            content = ""
            tool_calls = []


            async for chunk in self.llm.stream_tool_calling_async(state.messages, tools = self.mcp_client.tools):
                if isinstance(chunk, dict) and chunk.get('type') == 'content':
                    content += chunk.get('content', '')
                    stream_writer({'type': 'content', 'content': chunk.get('content', '')})

                elif isinstance(chunk, dict) and chunk.get('type') == 'function':
                    tool_calls.append(chunk)
                    stream_writer({'type': 'log', 'log': 'Identified tool call: ' + str(chunk) + '\n'})

        state.messages.append({
            'role': "assistant",
            "content": content,
            "tool_calls": tool_calls
        })

        return state
    

    async def finalize(self, state: AgentState) -> AgentState:
        if self.streaming:
            stream_writer = get_stream_writer()
            stream_writer({'type': 'state', 'state': state})
        return state

            
    def build_graph(self) -> Optional[StateGraph]:
        return None

    
    async def ainvoke(self, state: AgentState) -> AgentState:

        if not self.graph:
            raise ValueError("Workflow graph is not defined.")
        
        # Run the workflow
        state = await self.graph.ainvoke(state)
        if state is None:
            raise ValueError("Workflow execution returned None.")

        return state


    async def stream(self, state: AgentState, stream_mode="custom") -> AsyncIterable[Dict[str, Any]]:
        
        if not self.graph:
            raise ValueError("Workflow graph is not defined.")
        
        async for chunk in self.graph.astream(state, stream_mode=stream_mode):
            yield chunk
        

