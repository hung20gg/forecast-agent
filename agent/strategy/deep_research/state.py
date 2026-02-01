from core.state import AgentState

from typing import List, Dict, Any

conduct_research_tool = {
        "type": "function",
        "function": {
            "name": "conduct_research_tool",
            "description": "Get today's horoscope for an astrological sign.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sign": {
                        "type": "string",
                        "description": "An astrological sign like Taurus or Aquarius",
                    },
                },
                "required": ["sign"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }

think_tool = {
        "type": "function",
        "function": {
            "name": "think_tool",
            "description": "Get today's horoscope for an astrological sign.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reflection": {
                        "type": "string",
                        "description": "A reflection or thought related to the research process.",
                    },
                },
                "required": ["reflection"],
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
            "strict": True,
        },
    }

class DeepResearchState(AgentState):

    is_research_complete: bool = False
    raw_messages: List[Dict[str, Any]] = []
    supervisor_messages: List[Dict[str, Any]] = []
    
    
class ResearcherState(AgentState):

    raw_messages: List[Dict[str, Any]] = []
    