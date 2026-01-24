from langgraph.graph import StateGraph, START, END

from core.agent import BaseAgentMCP
from .state import ReActAgentState

class ReActAgent(BaseAgentMCP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build_graph(self) -> StateGraph:

        workflow = StateGraph(ReActAgentState)

        workflow.add_node('llm', self.tool_calling)
        workflow.add_node("tools", self.tool_execute)
        workflow.add_node("finalize", self.finalize)

        workflow.set_entry_point("llm")
        workflow.add_conditional_edges(
            "llm",
            self.is_finished,
            {
                'end': 'finalize',
                'continue': 'tools'
            }

        )
        workflow.add_edge("tools", "llm")
        workflow.add_edge("finalize", END)
        graph = workflow.compile()

        return graph
