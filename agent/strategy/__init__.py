import sys
from pathlib import Path

# Load environment config before any other imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
from env_config import load_env_config
load_env_config()

from core.agent import BaseAgentMCP, BaseAgentMCPConfig
from .react.agent import ReActAgent, ReActAgentConfig
from .react.state import ReActAgentState
from .deep_research.agent import OpenDeepResearchAgent, OpenDeepResearchAgentConfig, ResearcherAgent, ResearcherAgentConfig
from .deep_research.state import OpenDeepResearchState, ResearcherState

from typing import Union, Optional

def get_agent_config(agent_type: str, **kwargs) -> Union[ReActAgentConfig, OpenDeepResearchAgentConfig]:
    if agent_type == "react":
        return ReActAgentConfig(**kwargs)
    elif agent_type == "deep_research":
        return OpenDeepResearchAgentConfig(**kwargs)
    elif agent_type == "researcher":
        return ResearcherAgentConfig(**kwargs)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

def get_agent(config: BaseAgentMCPConfig) -> Union[ReActAgent, OpenDeepResearchAgent]:
    if config.agent_type == "react":
        return ReActAgent(config=config)
    elif config.agent_type == "deep_research":
        return OpenDeepResearchAgent(config=config)
    elif config.agent_type == "researcher":
        return ResearcherAgent(config=config)
    else:
        raise ValueError(f"Unknown agent config")
    
def get_agent_state(agent_type: str, **kwargs) -> Optional[type]:
    if agent_type == "react":
        return ReActAgentState(**kwargs)
    elif agent_type == "deep_research":
        return OpenDeepResearchState(**kwargs)
    elif agent_type == "researcher":
        return ResearcherState(**kwargs)
    else:
        return None
    
__all__ = ["ReActAgent", "OpenDeepResearchAgent", "get_agent_strategy", "get_agent_state"]