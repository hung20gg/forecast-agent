from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer
from langgraph.types import Command
import json
import asyncio
import os
from typing import Literal, Optional, List, Dict, Any


from core.agent import BaseAgentMCP, BaseAgentMCPConfig
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

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_clarify_with_user_prompt.md"), "r") as file:
    DEFAULT_CLARIFY_PROMPT = file.read()

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_write_research_brief_prompt.md"), "r") as file:
    DEFAULT_RESEARCH_BRIEF_PROMPT = file.read()

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_supervisor_system_prompt.md"), "r") as file:
    DEFAULT_RESEARCHER_SYSTEM_PROMPT = file.read()

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_supervisor_system_prompt.md"), "r") as file:
    DEFAULT_SUPERVISOR_SYSTEM_PROMPT = file.read()

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_researcher_compress_prompt.md"), "r") as file:
    DEFAULT_RESEARCHER_COMPRESS_PROMPT = file.read()

with open(os.path.join(CURRENT_DIR, '..', "..", "prompt", "deep_research_final_report_generation_prompt.md"), "r") as file:
    DEFAULT_FINAL_REPORT_PROMPT = file.read()


class OpenDeepResearchAgentConfig(BaseAgentMCPConfig):
    agent_type: str = "deep_research"
    max_clarify_iterations: int = 1
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


class ResearcherAgent(BaseAgentMCP):
    def __init__(self, config: ResearcherAgentConfig) -> None:
        super().__init__(config=config)
        self.config = config

    async def conduct_research(self, state: ResearcherState) -> ResearcherState:
        if len(state.messages) == 0:
            state.messages.append({
                "role": "system",
                "content": self.config.researcher_system_prompt.format(
                    current_time=self.config.current_time
                )
            })
            state.messages.append({
                "role": "user",
                "content": state.research_task
            })

        return await self.tool_calling(state)

    async def researcher_tool_execute(self, state: ResearcherState) -> ResearcherState:
        return await self.tool_execute(state)
    
    async def compress_research(self, state: ResearcherState) -> ResearcherState:
        
        state.messages.append({
            'role': 'user',
            'content': self.config.researcher_compress_prompt
        })

        response = await self.llm.ainvoke(state.messages)

        state.compressed_research = response
        return state
    
    def build_graph(self) -> StateGraph:
        
        workflow = StateGraph(ResearcherState)

        workflow.add_node('conduct_research', self.conduct_research)
        workflow.add_node('researcher_tool_execute', self.researcher_tool_execute)
        workflow.add_node('compress_research', self.compress_research)

        workflow.set_entry_point("conduct_research")
        workflow.add_edge("conduct_research", "researcher_tool_execute")
        workflow.add_conditional_edges(
            "researcher_tool_execute",
            self.is_tool_calling_finished,
            {
                'end': 'compress_research',
                'continue': 'conduct_research'
            }
        )
        workflow.add_edge("researcher_tool_execute", "compress_research")
        workflow.add_edge("compress_research", END)
        graph = workflow.compile()

        return graph
    

    async def ainvoke(self, state: ResearcherState) -> ResearcherState:
        if not self.graph:
            raise ValueError("Workflow graph is not defined.")
        
        # Run the workflow
        state = await self.graph.ainvoke(state)

        if state is None:
            raise ValueError("Workflow execution returned None.")

        return ResearcherState(**state)

class OpenDeepResearchAgent(BaseAgentMCP):
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

    async def clarify_with_user(self, state: OpenDeepResearchState) -> OpenDeepResearchState:
        
        print("[NODE] Clarify with user")
        if state.is_question_clarified:
            return state
        
        flatten_conv = flatten_messages(state.messages)

        temp_messages = [
            {
                "role": "user",
                "content": self.config.clarify_prompt.format(
                    messages=flatten_conv,
                    current_time=self.config.current_time
                )
            }
        ]

        if self.config.streaming:
            stream_writer = get_stream_writer()
            cache_text = ""
            current_text = ""
            is_question_clarified = False

            async for chunk in self.llm.astream(temp_messages):
                if len(current_text) < 10: 
                    cache_text += chunk
                    if '[NO]' in cache_text:
                        is_question_clarified = True
                        state.clarified_counter = 0
                    elif '[YES]' in cache_text:
                        is_question_clarified = False
                        stream_writer({'type': 'content', 'content': 'Fck, need to clarify more.\n'})
                        
                else:
                    # Stream if need to clarify
                    if not is_question_clarified:
                        if cache_text != '':
                            stream_writer({'type': 'content', 'content': cache_text})
                            cache_text = ""
                        stream_writer({'type': 'content', 'content': chunk})

                current_text += chunk
            if not is_question_clarified:
                state.is_question_clarified = False
                state.clarified_counter += 1
                
        else:
            response = await self.llm.ainvoke(temp_messages)
            content = response.get('content', '')

            if '[YES]' in content:
                state.is_question_clarified = False
                state.clarified_counter = 0
            elif '[NO]' in content:
                state.is_question_clarified = True
                state.clarified_counter += 1

        if not state.is_question_clarified:
            print("\nUser needs to clarify the question.\n")
        else:
            print("\nQuestion is clarified.\n")

        return state
                

            
    async def write_research_brief(self, state: OpenDeepResearchState) -> OpenDeepResearchState:
    
        if count_messages_words(state.messages) > 5000:
            summarized_messages = summarize_messages(self.llm, flatten_messages(state.messages))
            temp_messages = summarized_messages
        else:
            temp_messages = flatten_messages(state.messages)

        write_research_messages = [
            {
                "role": "system",
                "content": self.config.research_brief_prompt
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

    async def supervisor(self, state: OpenDeepResearchState) -> OpenDeepResearchState:
        
        if state.research_counter == 0:
            if len(state.supervisor_messages) == 0:

                supervisor_messages = [
                    {
                        "role": "system",
                        "content": self.config.supervisor_system_prompt
                    }
                ]
                state.supervisor_messages.extend(supervisor_messages)

            state.supervisor_messages.append(
                {
                    "role": "user",
                    "content": "## Research Briefs:\n" + state.research_briefs[-1]
                }
            )

        tool_calling_result = await self._tool_calling(messages=state.supervisor_messages, tools=self.mcp_client.tools)
        
        message = {
            'role': "assistant",
            "content": tool_calling_result.get("content")
        }
        
        if tool_calling_result.get("tool_calls"):
            message["tool_calls"] = tool_calling_result.get("tool_calls")
        
        state.supervisor_messages.append(message)

        return state

    
    async def supervisor_tool_execute(self, state: OpenDeepResearchState) -> OpenDeepResearchState:
        
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

        return state    
        

    async def final_report_generation(self, state: OpenDeepResearchState) -> OpenDeepResearchState:
        pass

    def is_question_clarified(self, state: OpenDeepResearchState) -> str:
        
        print(state)

        if state.clarified_counter > self.config.max_clarify_iterations:
            return 'clarified'

        if state.is_question_clarified:
            return 'clarified'
        return 'need_clarification'
    
    def is_research_complete(self, state: OpenDeepResearchState) -> str:
        
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

    async def ainvoke(self, state: OpenDeepResearchState) -> OpenDeepResearchState:
        if not self.graph:
            raise ValueError("Workflow graph is not defined.")
        
        # Run the workflow
        state = await self.graph.ainvoke(state)

        if state is None:
            raise ValueError("Workflow execution returned None.")

        return OpenDeepResearchState(**state)