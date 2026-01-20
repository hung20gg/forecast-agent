from agent.react import ReActAgent
from core.state import AgentState

import asyncio

async def main():
    agent_config = {
        "model_name": "gpt-4.1-mini"
    }
    state = AgentState()
    state.messages.append({
        "role":'user',
        "content": "Thông tin Vin đầu tư đường sẵt Bắc Nam trong năm 2025"
    })


    agent = ReActAgent(**agent_config)
    await agent.initialize()

    result = await agent.invoke(state)
    print(result)

if __name__ == "__main__":

    asyncio.run(main())