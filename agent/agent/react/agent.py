from langgraph.graph import StateGraph, START, END

from core.agent import BaseAgentMCP
from core.state import AgentState

class ReActAgent(BaseAgentMCP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build_graph(self) -> StateGraph:

        workflow = StateGraph(AgentState)

        workflow.add_node('llm', self.tool_calling)
        workflow.add_node("tools", self.tool_execute)

        workflow.set_entry_point("llm")
        workflow.add_conditional_edges(
            "llm",
            self.is_finished,
            {
                'end': END,
                'continue': 'tools'
            }

        )
        workflow.add_edge("tools", "llm")
        graph = workflow.compile()

        return graph
