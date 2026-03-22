from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer
from langgraph.types import Command
import json
import asyncio
import os
from typing import Literal, Optional, List, Dict, Any, AsyncIterable
import weave

from core.agent import BaseAgentMCP, BaseAgentMCPConfig
from core.logger import logger
from .state import (
    OpenDeepResearchState,
    ResearcherState,
    conduct_research_tool,
    research_complete_tool,
)
from ..utils import (
    flatten_messages,
    count_messages_words,
    summarize_messages
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_clarify_with_user_prompt.md"), "r", encoding="utf-8") as file:
    DEFAULT_CLARIFY_PROMPT = file.read()

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_write_research_brief_prompt.md"), "r", encoding="utf-8") as file:
    DEFAULT_RESEARCH_BRIEF_PROMPT = file.read()

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_researcher_system_prompt.md"), "r", encoding="utf-8") as file:
    DEFAULT_RESEARCHER_SYSTEM_PROMPT = file.read()

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_supervisor_system_prompt.md"), "r", encoding="utf-8") as file:
    DEFAULT_SUPERVISOR_SYSTEM_PROMPT = file.read()

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_researcher_compress_prompt.md"), "r", encoding="utf-8") as file:
    DEFAULT_RESEARCHER_COMPRESS_PROMPT = file.read()

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_final_report_generation_prompt.md"), "r", encoding="utf-8") as file:
    DEFAULT_FINAL_REPORT_PROMPT = file.read()


class OpenDeepResearchAgentConfig(BaseAgentMCPConfig):
    agent_type: str = "deep_research"
    max_clarify_iterations: int = 1
    max_supervisor_iterations: int = 5
    max_research_iterations: int = 20
    max_concurrent_researchers: int = 3
    clarify_prompt: str = DEFAULT_CLARIFY_PROMPT
    research_brief_prompt: str = DEFAULT_RESEARCH_BRIEF_PROMPT
    supervisor_system_prompt: str = DEFAULT_SUPERVISOR_SYSTEM_PROMPT
    final_report_prompt: str = DEFAULT_FINAL_REPORT_PROMPT


class ResearcherAgentConfig(BaseAgentMCPConfig):
    agent_type: str = "researcher"
    max_research_depth: int = 5
    researcher_system_prompt: str = DEFAULT_RESEARCHER_SYSTEM_PROMPT
    researcher_compress_prompt: str = DEFAULT_RESEARCHER_COMPRESS_PROMPT


class ResearcherAgent(BaseAgentMCP[ResearcherState, ResearcherAgentConfig]):
    def __init__(self, config: ResearcherAgentConfig) -> None:
        super().__init__(config=config)
        self.config = config

    @weave.op(call_display_name="Conduct Research")
    async def conduct_research(self, state: ResearcherState) -> ResearcherState:
        
        if len(state.messages) == 0:
            state.messages.append({
                "role": "system",
                "content": self.config.researcher_system_prompt.format(
                    current_time=state.current_time,
                    tool_notice=state.tool_notice
                )
            })
            state.messages.append({
                "role": "user",
                "content": state.research_task
            })

        return await self.tool_calling(state)

    @weave.op(call_display_name="Researcher Tool Execute")
    async def researcher_tool_execute(self, state: ResearcherState) -> ResearcherState:
        return await self.tool_execute(state)
    
    @weave.op(call_display_name="Compress Research")
    async def compress_research(self, state: ResearcherState) -> ResearcherState:
        
        flatten_conv = flatten_messages(state.messages)

        if state.messages[0]["role"] == "system":
            flatten_conv_for_tool_notice = flatten_messages(state.messages[1:-1])
        else:
            flatten_conv_for_tool_notice = flatten_messages(state.messages[:-1])

        tool_notice_prompt = """
        You are an agent specialized in updating tool notice for researcher agent.

        Here is the previous tool notice: {tool_notice}
        
        You should ignore most of the research content and focus solely on the tool calling. The system might face trouble with the tool calling and require multiple iterations to call the tool correctly, 
        so you need to update the tool notice to help the system call the tool correctly.
        
        Return the updated tool notice only. DO NOT repeat the previous tool notice. DO NOT ADD ANY EXTRA INFORMATION.
        
        """

        summarize_messages = [
            {
                "role": "system",
                "content": self.config.researcher_compress_prompt.format(
                    current_time=state.current_time
                )
            },
            {
                "role": "user",
                "content": flatten_conv
            }
        ]

        update_tool_notice_messages = [
            {
                "role": "system",
                "content": tool_notice_prompt.format(
                    tool_notice=state.tool_notice
                )
            },
            {
                "role": "user",
                "content": flatten_conv_for_tool_notice
            }
        ]
        
        compressed_research, update_tool_notice = await asyncio.gather(
            self.llm.ainvoke(summarize_messages),
            self.llm.ainvoke(update_tool_notice_messages),
        )
        state.compressed_research = compressed_research
        state.tool_notice += "\n" + update_tool_notice
        return state

    def build_graph(self) -> StateGraph:
        
        workflow = StateGraph(ResearcherState)

        workflow.add_node('conduct_research', self.conduct_research)
        workflow.add_node('researcher_tool_execute', self.researcher_tool_execute)
        workflow.add_node('compress_research', self.compress_research)

        workflow.set_entry_point("conduct_research")
        workflow.add_conditional_edges(
            "conduct_research",
            self.is_tool_calling_finished,
            {
                'end': "compress_research", # fan-out
                'continue': 'researcher_tool_execute'
            }
        )
        workflow.add_edge("researcher_tool_execute","conduct_research")
        
        workflow.add_edge("compress_research", END)
        graph = workflow.compile()

        return graph
    
    @weave.op(call_display_name="Invoke Research Agent")
    async def ainvoke(self, state: ResearcherState) -> ResearcherState:
        return await super().ainvoke(state)
    
    @weave.op(call_display_name="Stream Research Agent")
    async def stream(self, state: ResearcherState, stream_mode="custom") -> AsyncIterable[Dict[str, Any]]:
        async for chunk in super().stream(state, stream_mode=stream_mode):
            yield chunk

class OpenDeepResearchAgent(BaseAgentMCP[OpenDeepResearchState, OpenDeepResearchAgentConfig]):
    def __init__(self,  config : OpenDeepResearchAgentConfig, researcher_agent: Optional[ResearcherAgent] = None) -> None:
        super().__init__(config= config)
        
        self.config = config
        self.researcher_agent = researcher_agent
        self.openai_deep_research_tools = [
            conduct_research_tool, 
            research_complete_tool
        ]

    def register_researcher_agent(self, researcher_agent: ResearcherAgent):
        self.researcher_agent = researcher_agent

    @weave.op(call_display_name="Clarify with User")
    async def clarify_with_user(self, state: OpenDeepResearchState) -> OpenDeepResearchState:
        logger.info("[NODE] - Clarify with User")
        if state.is_question_clarified:
            return state
        
        state.messages.append(
                {
                    "role": "user",
                    "content": state.user_request
                }
            )
        
        flatten_conv = flatten_messages(state.messages)

        temp_messages = [
            {
                "role": "user",
                "content": self.config.clarify_prompt.format(
                    messages=flatten_conv,
                    current_time=state.current_time
                )
            }
        ]

        if self.config.streaming:

            stream_writer = get_stream_writer()
            cache_text = ""
            current_text = ""
            is_question_clarified = False

            async for chunk in self.llm.astream(temp_messages):
                stream_writer({'type': 'content', 'content': chunk})
                if len(current_text) < 5: 
                    cache_text += chunk
                    if '[NO]' in cache_text:
                        state.is_question_clarified = True
                        logger.info("[NO] - Question is clarified.\n")
                        break
                    elif '[YES]' in cache_text:
                        state.is_question_clarified = False
                        
                current_text += chunk
            if not is_question_clarified:
                state.is_question_clarified = False
                state.clarified_counter += 1
                
        else:
            response = await self.llm.ainvoke(temp_messages)
            content = response.get('content', '')

            if '[YES]' in content:
                state.is_question_clarified = False
            elif '[NO]' in content:
                state.is_question_clarified = True
                    

        if not state.is_question_clarified:
            state.clarified_counter += 1
            logger.info("[YES] -  User needs to clarify the question.\n")
        else:
            state.clarified_counter = 0
            logger.info("[NO] - Question is clarified.\n")

        return state
                

    @weave.op(call_display_name="Write Research Brief")    
    async def write_research_brief(self, state: OpenDeepResearchState) -> OpenDeepResearchState:
        logger.info("[NODE] - Write Research Brief")

        if count_messages_words(state.messages) > 5000:
            summarized_messages = summarize_messages(self.llm, flatten_messages(state.messages))
            temp_messages = summarized_messages
        else:
            temp_messages = flatten_messages(state.messages)

        write_research_messages = [
            {
                "role": "system",
                "content": self.config.research_brief_prompt.format(
                    current_time=state.current_time
                )
            },
            {
                "role": "user",
                "content": temp_messages
            }
        ]
        if self.config.streaming:
            stream_writer = get_stream_writer()
            response = ""
            async for chunk in self.llm.astream(write_research_messages):
                stream_writer({'type': 'content', 'content': chunk})
                response += chunk
        else:
            response = await self.llm.ainvoke(write_research_messages)
        research_brief = response
        state.research_briefs.append(research_brief)

        return state

    @weave.op(call_display_name="Supervisor")
    async def supervisor(self, state: OpenDeepResearchState) -> OpenDeepResearchState:
        logger.info("[NODE] - Supervisor")
        if state.supervisor_counter == 0:
            if len(state.supervisor_messages) == 0:

                supervisor_messages = [
                    {
                        "role": "system",
                        "content": self.config.supervisor_system_prompt.format(
                            current_time=state.current_time,
                            max_research_iterations = self.config.max_supervisor_iterations,
                            max_concurrent_researchers = self.config.max_concurrent_researchers
                        )
                    }
                ]
                state.supervisor_messages.extend(supervisor_messages)

            state.supervisor_messages.append(
                {
                    "role": "user",
                    "content": "## Research Briefs:\n" + state.research_briefs[-1]
                }
            )

        tool_calling_result = await self._tool_calling(messages=state.supervisor_messages, tools=self.openai_deep_research_tools)
        
        message = {
            'role': "assistant",
            "content": tool_calling_result.get("content")
        }
        
        if tool_calling_result.get("tool_calls"):
            message["tool_calls"] = tool_calling_result.get("tool_calls")
        
        state.supervisor_messages.append(message)
        state.supervisor_counter += 1

        logger.info(f"Supervisor generated message with content length: {len(message['content'])} and {len(message.get('tool_calls', []))} tool calls.")

        return state

    
    @weave.op(call_display_name="Supervisor Tool Execute")
    async def supervisor_tool_execute(self, state: OpenDeepResearchState) -> OpenDeepResearchState:
        logger.info("[NODE] - Supervisor Tool Execute")
        recent_supervisor_command = state.supervisor_messages[-1]
        
        # Check for finish signal from supervisor
        if 'tool_calls' in recent_supervisor_command:
            for tool_response in recent_supervisor_command.get("tool_calls", []):
                print('Supervisor executing tool call:', tool_response)
                tool_id = tool_response.get("id")
                function = tool_response.get("function")
                if function.get("name") == research_complete_tool['function']['name']:
                    print("Research marked as complete by supervisor.")
                    
                    state.is_research_complete = True
                    return state
        else:                        
            return state
        thinking_content = recent_supervisor_command.get("content", "")

        all_tool_calls = recent_supervisor_command.get("tool_calls", [])
        allowed_tool_calls =  all_tool_calls[:self.config.max_research_iterations]  # Only allow first tool call (researcher interaction)
        overflow_tool_calls = all_tool_calls[self.config.max_research_iterations:]  # Remaining tool calls to be ignored
        
        logger.info(f"Incrementing research counter by {len(allowed_tool_calls)}")
        state.research_counter += len(allowed_tool_calls)

        research_task_states = []
        for tool_response in allowed_tool_calls:
            print('Supervisor executing tool call:', tool_response)
            tool_id = tool_response.get("id")
            function = tool_response.get("function")
            function_name = function.get("name")

            if function_name == conduct_research_tool['function']['name']:
                arguments = json.loads(function.get("arguments"))
                research_task_state = ResearcherState(
                    task_id = tool_id,
                    research_task = arguments.get("research_task", ""),
                    tool_notice = state.global_tool_notice,
                    current_time = state.current_time
                )
                research_task_states.append(research_task_state)

        if self.researcher_agent is None:
            raise ValueError("Researcher agent is not registered.")
        research_tasks = [
            self.researcher_agent.ainvoke(research_task_state) 
            for research_task_state in research_task_states
        ]

        state.research_tasks.extend(research_task_states)

        research_results = await asyncio.gather(*research_tasks)
        research_tool_responses = [res_state.to_tool_response() for res_state in research_results]
        overflow_tool_responses = [
            {
                "role": "tool",
                "tool_call_id": tool_response.get("id"),
                "content": "Tool call ignored due to exceeding maximum allowed research iterations."
            } for tool_response in overflow_tool_calls
        ]

        state.supervisor_messages.extend(research_tool_responses + overflow_tool_responses)          

        # Update tool notice
        max_tool_call = 0
        update_tool_notice = ""
        for research_state in research_results:
            if research_state.num_tool_calls > max_tool_call:
                max_tool_call = research_state.num_tool_calls
                update_tool_notice = research_state.tool_notice
        
        state.global_tool_notice = update_tool_notice

        return state    
        
    @weave.op(call_display_name="Final Report Generation")
    async def final_report_generation(self, state: OpenDeepResearchState) -> OpenDeepResearchState:
        logger.info("[NODE] - Final Report Generation")
        flatten_supervisor_messages = flatten_messages(state.supervisor_messages)

        final_report_messages = [
            {
                "role": "system",
                "content": self.config.final_report_prompt.format(
                    current_time=self.config.current_time
                )
            },
            {
                "role": "user",
                "content": """

        <User Request>
        {user_request}
        </User Request>
                        
        <Research Brief>
        {research_brief}
        </Research Brief>

        <Findings>
        {findings}
        </Findings>

        """.format(
                    user_request=state.user_request,
                    research_brief=state.research_briefs[-1] if state.research_briefs else "",
                    findings=flatten_supervisor_messages)
            }
        ]

        if self.config.streaming:
            stream_writer = get_stream_writer()
            response = ""
            async for chunk in self.llm.astream(final_report_messages):
                stream_writer({'type': 'content', 'content': chunk})
                response += chunk
        else:
            response = await self.llm.ainvoke(final_report_messages)
        
        state.final_report = response

        return state

    def is_question_clarified(self, state: OpenDeepResearchState) -> str:
        
        if state.clarified_counter > self.config.max_clarify_iterations:
            return 'clarified'

        if state.is_question_clarified:
            return 'clarified'
        return 'need_clarification'
    
    def is_research_complete(self, state: OpenDeepResearchState) -> str:

        if state.supervisor_counter > self.config.max_supervisor_iterations:
            return 'complete'
        
        if state.research_counter > self.config.max_research_iterations:
            return 'complete'
        
        if state.is_research_complete:
            return 'complete'
        return 'incomplete'
    
    def build_graph(self) -> StateGraph:

        workflow = StateGraph(OpenDeepResearchState)

        workflow.add_node('clarify_with_user', self.clarify_with_user)
        workflow.add_node('write_research_brief', self.write_research_brief)
        workflow.add_node('supervisor', self.supervisor)
        workflow.add_node('supervisor_tool_execute', self.supervisor_tool_execute)
        workflow.add_node('final_report_generation', self.final_report_generation)

        workflow.set_entry_point("clarify_with_user")
        workflow.add_conditional_edges(
            "clarify_with_user",
            self.is_question_clarified,
            {
                'clarified': 'write_research_brief',
                'need_clarification': END
            }
        )
        workflow.add_edge("write_research_brief", "supervisor")
        workflow.add_edge("supervisor", "supervisor_tool_execute")
        workflow.add_conditional_edges(
            "supervisor_tool_execute",
            self.is_research_complete,
            {
                'complete': 'final_report_generation',
                'incomplete': 'supervisor'
            }
        )
        workflow.add_edge("final_report_generation", END)
        graph = workflow.compile()
        return graph

    @weave.op(call_display_name="Invoke Open Deep Research Agent")
    async def ainvoke(self, state: ResearcherState) -> ResearcherState:
        return await super().ainvoke(state)
    
    @weave.op(call_display_name="Stream Open Deep Research Agent")
    async def stream(self, state: ResearcherState, stream_mode="custom") -> AsyncIterable[Dict[str, Any]]:
        async for chunk in super().stream(state, stream_mode=stream_mode):
            yield chunk
