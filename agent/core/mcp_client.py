from fastmcp import Client
import fastmcp
from typing import Dict, List, Any, Optional
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

def _fastmcp_to_openai_tools(tools) -> list:
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

class MCPClient:
    def __init__(self):
        url = os.getenv("MCP_SERVER_URL")
        self.client = Client(url)
        self.tools: Optional[List[Dict[str, Any]]] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the client and load tools"""
        if not self._initialized:
            async with self.client:
                tools = await self.client.list_tools()
                self.tools = _fastmcp_to_openai_tools(tools)
                self._initialized = True

    async def _ensure_initialized(self) -> None:
        """Ensure client is initialized before use"""
        if not self._initialized:
            await self.initialize()

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        await self._ensure_initialized()
        async with self.client:
            return await self.client.call_tool(tool_name, params)

    def call_tool_sync(self, function_name: str, arguments: dict):
        """Synchronous wrapper for call_tool"""
        return asyncio.run(self.call_tool(function_name, arguments))
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools (must call initialize first)"""
        if not self._initialized:
            raise RuntimeError("MCPClient not initialized. Call await client.initialize() first")
        return self.tools