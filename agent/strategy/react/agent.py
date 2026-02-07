from langgraph.graph import StateGraph, START, END
import os
import weave

from core.agent import BaseAgentMCP, BaseAgentMCPConfig
from core.logger import logger
from .state import ReActAgentState


current_dir = os.path.dirname(os.path.abspath(__file__))
prompt_path = os.path.join(current_dir, '..', "..", "prompt", "react_system_prompt.md")
with open(prompt_path, "r") as file:
    REACT_SYSTEM_PROMPT = file.read()

class ReActAgentConfig(BaseAgentMCPConfig):
    agent_type: str = "react"
    max_tool_calls: int = 5

class ReActAgent(BaseAgentMCP[ReActAgentState, ReActAgentConfig]):
    def __init__(self, config: ReActAgentConfig) -> None:
        super().__init__(config=config)

    @weave.op(call_display_name="ReAct Tool Calling")
    async def tool_calling(self, state: ReActAgentState) -> ReActAgentState:
        
        if len(state.messages) == 0:
            state.messages.append(
                {
                    "role": "system",
                    "content": REACT_SYSTEM_PROMPT.format(
                        current_time=self.config.current_time,
                        maximum_iterations=self.config.max_tool_calls
                    )
                }
            )
        if state.messages[0]['role'] != 'system':
            state.messages.insert(0,
                {
                    "role": "system",
                    "content": REACT_SYSTEM_PROMPT.format(
                        current_time=self.config.current_time,
                        maximum_iterations=self.config.max_tool_calls
                    )
                }
            )

        if state.current_iteration == 0:
            state.current_iteration += 1
            state.messages.append(
                {
                    "role": "user",
                    "content": state.user_request
                }
            )




        last_message = state.messages[-1]['content']
        if isinstance(last_message, str):
            last_message += "\nMaximum tool calls: {}".format(self.config.max_tool_calls)

        elif isinstance(last_message, list):
            last_message.append(
                {
                    'type': 'text',
                    'text': "Maximum tool calls: {}".format(self.config.max_tool_calls)
                }
            )

        state.messages[-1]['content'] = last_message

        return await super().tool_calling(state)

    @weave.op(call_display_name="Finalize React Agent State")
    async def finalize(self, state: ReActAgentState) -> ReActAgentState:

        state.current_iteration = 0  # Reset iteration for next invocation
        return await super().finalize(state)


    def build_graph(self) -> StateGraph:

        workflow = StateGraph(ReActAgentState)

        workflow.add_node('llm', self.tool_calling)
        workflow.add_node("tools", self.tool_execute)
        workflow.add_node("finalize", self.finalize)

        workflow.set_entry_point("llm")
        workflow.add_conditional_edges(
            "llm",
            self.is_tool_calling_finished,
            {
                'end': 'finalize',
                'continue': 'tools'
            }

        )
        workflow.add_edge("tools", "llm")
        workflow.add_edge("finalize", END)
        graph = workflow.compile()

        return graph


    # async def ainvoke(self, state: ReActAgentState) -> ReActAgentState:
    #     """Asynchronously invoke the agent with the given state"""

    #     if not self.graph:
    #         raise ValueError("Workflow graph is not defined.")
        
    #     # Run the workflow
    #     with weave.thread(self.session_id) as thread_ctx:
    #         logger.info(f"Starting agent invocation with thread ID: {self.session_id}")
    #         state = await self.graph.ainvoke(state)

    #     if state is None:
    #         raise ValueError("Workflow execution returned None.")

    #     return ReActAgentState(**state)
        