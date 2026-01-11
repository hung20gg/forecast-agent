import asyncio
from fastmcp import Client

host = "http://localhost"
port = 9003
# HTTP server
url = f"{host}:{port}/mcp"
print(f"Connecting to MCP server at {url}...")
client = Client(url)

async def main():
    async with client:
        # Basic server interaction
        await client.ping()
        
        # List available operations
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()
        
        # Execute operations
        result = await client.call_tool("get_stock_value", {"stock_symbol": "VIC", "start_date": "2023-01-01", "end_date": "2023-10-01", "duration": "monthly"})
        print(tools)
        
        print(resources)
        
        print(prompts)
        
        print(result.content)

asyncio.run(main())