from typing import Annotated, List, TypedDict, Dict, Any
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class AgentState:
    """The state of the agent."""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    number_of_steps: int = 0