from langgraph.graph import StateGraph, START, END

from core.agent import BaseAgentMCP
from core.state import AgentState


class OpenDeepResearchAgent(BaseAgentMCP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    async def write_research_brief(self, state: AgentState) -> AgentState:
        pass


    async def final_report_generation(state)
    