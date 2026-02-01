from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer
from langgraph.types import Command

from typing import Literal


from core.agent import BaseAgentMCP, BaseAgentMCPConfig
from .state import (
    DeepResearchState,
    ResearcherState,
    conduct_research_tool,
    think_tool,
    research_complete_tool,
)


class OpenDeepResearchAgentConfig(BaseAgentMCPConfig):
    max_research_iterations: int = 5

class ResearcherAgent(BaseAgentMCP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def conduct_research(self, state: ResearcherState) -> ResearcherState:
        pass

    async def researcher_tools(self, state: ResearcherState) -> ResearcherState:
        pass
    
    async def compress_research(self, state: ResearcherState) -> ResearcherState:
        pass

class OpenDeepResearchAgent(BaseAgentMCP):
    def __init__(self, researcher_agent: ResearcherAgent, config : OpenDeepResearchAgentConfig):
        super().__init__(config= config)
        
        self.config = config
        self.researcher_agent = researcher_agent
        self.openai_deep_research_tools = [
            conduct_research_tool, 
            think_tool, 
            research_complete_tool
        ]

    async def clarify_with_user(self, state: DeepResearchState) -> DeepResearchState:
        pass

    async def supervisor(self, state: DeepResearchState) -> DeepResearchState:
        pass
    
    async def supervisor_tools(self, state: DeepResearchState) -> DeepResearchState:
        
        recent_supervisor_command = state.supervisor_messages[-1]
        
        # Check for finish signal from supervisor
        if 'tool_calls' in recent_supervisor_command:
            for tool_response in recent_supervisor_command.get("tool_calls", []):
                print('Supervisor executing tool call:', tool_response)
                tool_id = tool_response.get("id")
                function = tool_response.get("function")
                if function.get("name") == think_tool['function']['name']:
                    print("Research marked as complete by supervisor.")
                    
                    state.is_research_complete = True
                    return state
        else:                        
            return state
        all_tool_calls = recent_supervisor_command.get("tool_calls", [])
        allowed_tool_calls =  all_tool_calls[:self.config.max_research_iterations]  # Only allow first tool call (researcher interaction)
        overflow_tool_calls = all_tool_calls[self.config.max_research_iterations:]  # Remaining tool calls to be ignored
        
        research_tasks = []
        
        


    async def final_report_generation(self, state: DeepResearchState) -> DeepResearchState:
        pass
    