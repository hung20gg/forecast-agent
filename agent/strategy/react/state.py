import os
from dataclasses import dataclass, field
from typing import List, Dict, Any

from core.state import AgentState

current_dir = os.path.dirname(os.path.abspath(__file__))
prompt_path = os.path.join(current_dir, '..', "..", "prompt", "react_system_prompt.md")
with open(prompt_path, "r") as file:
    REACT_SYSTEM_PROMPT = file.read()

@dataclass
class ReActAgentState(AgentState):
    system_prompt: str = REACT_SYSTEM_PROMPT
    max_iterations: int = 5
    # messages inherited from AgentState - override default value
    messages: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "role": "system",
            "content": REACT_SYSTEM_PROMPT
        }
    ])