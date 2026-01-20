from llm import get_llm_wrapper
from core.mcp_client import MCPClient
from core.state import AgentState

from typing import Optional
from langgraph.graph import StateGraph
import json

class BaseAgentMCP:
    def __init__(self, model_name: str, message_saver: Optional[str] = None) -> None:
        self.llm = get_llm_wrapper(model_name)
        self.mcp_client = MCPClient()
        self._initialized = False
        self.graph = self.build_graph()


        if message_saver == 'mongodb':
            from llm.llm_logger.log_mongodb import LLMLogMongoDB
            self.llm = LLMLogMongoDB(llm=self.llm)
     
        elif message_saver == 'postgres':
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


    def is_finished(self, state: AgentState):
        if len(state.messages[-1].get("tool_calls", [])) == 0:
            return 'end'
        return 'continue'


    async def tool_execute(self, state: AgentState):

        tool_messages = []
        for tool_response in state.messages[-1].get("tool_calls", []):
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
    

    async def tool_calling(self, state: AgentState):

        tool_responses = await self.llm.tool_calling_async(messages=state.messages, tools = self.mcp_client.tools)
        
        content = tool_responses.get('content')
        tool_calls = tool_responses.get('tool_calls')

        state.messages.append({
            'role': "assistant",
            "content": content,
            "tool_calls": tool_calls
        })

        return state
            
    def build_graph(self):
        pass

    
    async def invoke(self, state: AgentState) -> AgentState:

        if not self.graph:
            raise ValueError("Workflow graph is not defined.")
        
        # Run the workflow
        state = await self.graph.ainvoke(state)
        if state is None:
            raise ValueError("Workflow execution returned None.")

        return state


