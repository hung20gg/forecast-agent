from strategy import get_agent_state, get_agent_config, get_agent
import json
from dataclasses import asdict

import asyncio

async def test_react():
    agent_config = {
        "agent_type": "react",
        "streaming": True,
        "model_name": "gpt-4.1-mini",
        "urls" : ["http://localhost:9003/sse"]
    }

    agent_state_config = {
        "agent_type": "react"
    }

    state = get_agent_state(**agent_state_config)
    state.user_request = "Tổng hợp các thông tin mới nhất về Vingroup trong năm 2025"

    agent_config = get_agent_config(**agent_config)

    agent = get_agent( config=agent_config)
    await agent.initialize()

    # result = await agent.invoke(state)
    # print(json.dumps(result, ensure_ascii=False, indent=2))
    async for chunk in agent.stream(state, stream_mode="custom"):
        if chunk.get('type') == 'content':
            print(chunk.get('content'), end='', flush=True)


async def test_researcher():
    researcher_agent_config = {
        "agent_type": "researcher",
        "streaming": False,
        "model_name": "gpt-4.1-mini",
        "urls" : ["http://localhost:9003/sse"]
    }

    researcher_state_config = {
        "agent_type": "researcher"
    }

    state = get_agent_state(**researcher_state_config)
    state.research_task = "Conduct a comprehensive analysis to forecast Vingroup\'s revenue for the first quarter of 2026. The research should include: 1) Vingroup\'s historical quarterly financial performance data, especially focusing on recent trends and patterns; 2) Recent business developments and strategic initiatives by Vingroup that could impact revenue; 3) Market analyses and industry trends relevant to Vingroup\'s sectors of operation; 4) Macroeconomic conditions and economic indicators in Vietnam that could influence Vingroup\'s revenue growth prospects. The goal is to synthesize these elements to provide an accurate revenue forecast for Q1 2026."

    agent_config = get_agent_config(**researcher_agent_config)

    researcher_agent = get_agent( config=agent_config)
    await researcher_agent.initialize()

    result = await researcher_agent.ainvoke(state)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


async def test_deep_research():
    deep_research_config = {
        "agent_type": "deep_research",
        "streaming": True,
        "model_name": "gpt-4.1-mini",
        "urls" : ["http://localhost:9003/sse"]
    }

    deep_research_state_config = {
        "agent_type": "deep_research"
    }

    researcher_agent_config = {
        "agent_type": "researcher",
        "streaming": False,
        "model_name": "gpt-4.1-mini",
        "urls" : ["http://localhost:9003/sse"]
    }

    dr_state = get_agent_state(**deep_research_state_config)
    dr_state.user_request = "Dự đoán doanh thu  của VIC."

    agent_config = get_agent_config(**deep_research_config)

    dr_agent = get_agent( config=agent_config)
    await dr_agent.initialize()


    researcher_agent_config = get_agent_config(**researcher_agent_config)
    researcher_agent = get_agent( config=researcher_agent_config)
    await researcher_agent.initialize()

    dr_agent.register_researcher_agent(researcher_agent)

    # result = await agent.invoke(state)
    # print(json.dumps(result, ensure_ascii=False, indent=2))
    response = ""
    async for chunk in dr_agent.stream(dr_state, stream_mode="custom"):
        if chunk.get('type') == 'content':
            print(chunk.get('content'), end='', flush=True)
            response += chunk.get('content')

    dr_state.messages.extend(
        [
            {
                "role": "assistant",
                "content": response
            }
        ]

    )

    dr_state.user_request = "Hãy tổng hợp các thông tin nghiên cứu và đưa ra dự đoán cho quý 1 2026 của VINGROUP."

    async for chunk in dr_agent.stream(dr_state, stream_mode="custom"):
        if chunk.get('type') == 'content':
            print(chunk.get('content'), end='', flush=True)
            response += chunk.get('content')

if __name__ == "__main__":

    asyncio.run(test_react())