import asyncio
from typing import Dict, Any
from fastmcp import Client

class MCPClient:
    """
    MCP client for connecting to and using tools provided by FastMCP server.
    """
    def __init__(self, mcp_server_url: str = "http://localhost:8000/mcp"):
        """
        Initialize the MCP client.

        Args:
            mcp_server_url: URL of the MCP server, defaults to "http://localhost:8000/mcp"
        """
        self.mcp_server_url = mcp_server_url
        self.client = Client(mcp_server_url)

    async def list_tools(self) -> Dict[str, Any]:
        """
        Get all available tools on the MCP server.

        Returns:
            Dictionary containing all tool information.
        """
        try:
            async with self.client:
                tools = await self.client.list_tools()
                print(tools)
                return {"tools": tools }
        except Exception as e:
            print(f"❌ Failed to get tool list: {e}")
            return {"tools": []}

    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Call a specific tool on the MCP server.

        Args:
            tool_name: Name of the tool
            params: Tool parameters

        Returns:
            Tool invocation result.
        """
        try:
            async with self.client:
                result = await self.client.call_tool(tool_name, params or {})
                return result
        except Exception as e:
            print(f"❌ Failed to call tool {tool_name}: {e}")
            return {"error": str(e)}

if __name__ == '__main__':
    client = MCPClient()
    tools = asyncio.run(client.list_tools())
