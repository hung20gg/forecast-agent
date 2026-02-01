from strategy import get_agent_state, get_agent_config, get_agent
import json

import asyncio

async def main():
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

if __name__ == "__main__":

    asyncio.run(main())