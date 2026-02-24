from core.state import AgentState

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

conduct_research_tool = {
        "type": "function",
        "function": {
            "name": "conduct_research_tool",
            "description": "Conduct a research task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "research_task": {
                        "type": "string",
                        "description": "The specific research task to be conducted.",
                    },
                },
                "required": ["research_task"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }


research_complete_tool = {
        "type": "function",
        "function": {
            "name": "research_complete_tool",
            "description": "Flag to indicate that research is complete.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "strict": True,
        },
    }

@dataclass
class ResearcherState(AgentState):

    task_id: Optional[str] = None
    research_task: Optional[str] = None
    compressed_research: Optional[str] = None
    tool_notice: str = ""

    def to_tool_response(self) -> Dict[str, Any]:
        return {
            "role": 'tool',
            "tool_call_id": self.task_id,
            "content": self.compressed_research or "",
        }
@dataclass
class OpenDeepResearchState(AgentState):
    
    is_question_clarified: bool = False
    global_tool_notice: str = ""
    clarified_counter: int = 0
    is_research_complete: bool = False
    research_briefs: List[str] = field(default_factory=list)
    research_counter: int = 0
    supervisor_counter: int = 0
    final_report: Optional[str] = None
    raw_messages: List[Dict[str, Any]] = field(default_factory=list)
    supervisor_messages: List[Dict[str, Any]] = field(default_factory=list)
    research_tasks: List[ResearcherState] = field(default_factory=list)


    

    