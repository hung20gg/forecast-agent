import asyncio
import json
from fastmcp import Client
import fastmcp
from llm import get_llm_wrapper
from typing import List, Dict, Union, Any

host = "http://localhost"
port = 9003
# HTTP server
url = f"{host}:{port}/sse"
print(f"Connecting to MCP server at {url}...")
client = Client(url)


llm = get_llm_wrapper("groq:openai/gpt-oss-120b")

def fastmcp_to_openai_tools(tools) -> list:
    openai_tools = []
    
    for tool in tools:
        tool = tool.model_dump()
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "parameters": tool.get("inputSchema", {}),
            }
        }
        openai_tools.append(openai_tool)
    return openai_tools

async def main():
    async with client:
        # Basic server interaction
        await client.ping()
        
        # List available operations
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()
        
        openai_tools = fastmcp_to_openai_tools(tools)
        print("Converted tools to OpenAI format:")
        print(openai_tools)
        # Execute operations
        result = await client.call_tool("query_relevant_news", {"query": "VIC", "start_date": "2025-01-01", "end_date": "2025-06-01", "channel": None})
        print("Tool call result:")
        print(result)
        
        # messages = [
        #     {
        #         "role": "user",
        #         "content": "Tin tức từ VIC từ 1/1/2025 đến 1/6/2025"
        #     }
        # ]
        

        # tool_responses = llm.tool_calling(messages, tools=openai_tools)
        
        # messages.append({
        #     "role": "assistant",
        #     "tool_calls": tool_responses
        # })
        
        # print(tool_responses)
        # for tool_response in tool_responses:
        #     tool_id = tool_response.get("id")
        #     function = tool_response.get("function")
        #     function_name = function.get("name")
        #     arguments = json.loads(function.get("arguments"))
            
        #     tool_result = await client.call_tool(function_name, arguments)
            
        #     messages.append({
        #         "role": "tool",
        #         "tool_call_id": tool_id,
        #         "content": json.dumps(tool_result.content[0].text)
        #     })
            
        # response = llm(messages)
        
        # print("Final LLM response:")
        # print(response)
            
        
        # print(tool_responses)
asyncio.run(main())