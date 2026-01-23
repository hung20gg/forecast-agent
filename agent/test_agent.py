from agent import ReActAgent
from core.state import AgentState

import asyncio

async def main():
    agent_config = {
        "model_name": "gpt-4.1-mini"
    }
    state = AgentState()
    state.messages.append({
        "role":'user',
        "content": "Dựa vào các công cụ sẵn có, dự đoán doanh thu quý 4 năm 2025 của VINGROUP. Bạn mới chỉ có dữ liệu quý 3 thôi. Hãy đưa ra dự đoán"
    })


    agent = ReActAgent(**agent_config)
    await agent.initialize()

    result = await agent.invoke(state)
    print(result)

if __name__ == "__main__":

    asyncio.run(main())