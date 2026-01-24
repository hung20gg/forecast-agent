from .react.agent import ReActAgent
from .react.state import ReActAgentState
from .deep_research.agent import OpenDeepResearchAgent

from typing import Union, Optional

def get_agent_strategy(agent_type: str, **kwargs) -> Union[ReActAgent, OpenDeepResearchAgent]:
    if agent_type == "react":
        return ReActAgent(**kwargs)
    elif agent_type == "deep_research":
        return OpenDeepResearchAgent(**kwargs)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
def get_agent_state(agent_type: str, **kwargs) -> Optional[type]:
    if agent_type == "react":
        return ReActAgentState(**kwargs)
    elif agent_type == "deep_research":
        return None  # Assuming OpenDeepResearchAgent uses AgentState
    else:
        return None
    
__all__ = ["ReActAgent", "OpenDeepResearchAgent", "get_agent_strategy", "get_agent_state"]