from strategy import get_agent_state, get_agent_config, get_agent
import json

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
    state.user_request = "Dựa vào các công cụ sẵn có, dự đoán doanh thu quý 4 năm 2025 của VINGROUP. Bạn mới chỉ có dữ liệu quý 3 thôi. Hãy đưa ra dự đoán"

    agent_config = get_agent_config(**agent_config)

    agent = get_agent( config=agent_config)
    await agent.initialize()

    # result = await agent.invoke(state)
    # print(json.dumps(result, ensure_ascii=False, indent=2))
    async for chunk in agent.stream(state, stream_mode="custom"):
        if chunk.get('type') == 'content':
            print(chunk.get('content'), end='', flush=True)


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
    dr_state.user_request = "Dựa vào các công cụ sẵn có, dự đoán doanh thu quý 4 năm 2025 của VINGROUP. Bạn mới chỉ có dữ liệu quý 3 thôi. Hãy đưa ra dự đoán"

    agent_config = get_agent_config(**deep_research_config)

    dr_agent = get_agent( config=agent_config)
    await dr_agent.initialize()


    researcher_agent_config = get_agent_config(**researcher_agent_config)
    researcher_agent = get_agent( config=researcher_agent_config)
    await researcher_agent.initialize()

    dr_agent.register_researcher_agent(researcher_agent)

    # result = await agent.invoke(state)
    # print(json.dumps(result, ensure_ascii=False, indent=2))
    async for chunk in dr_agent.stream(dr_state, stream_mode="custom"):
        if chunk.get('type') == 'content':
            print(chunk.get('content'), end='', flush=True)


if __name__ == "__main__":

    asyncio.run(test_react())