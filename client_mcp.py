import asyncio
from typing import Dict, Any
from fastmcp import Client

class MCP_Client:
    """
    MCP客户端，用于连接和使用FastMCP服务器提供的工具
    """
    def __init__(self, mcp_server_url: str = "http://localhost:8000/mcp"):
        """
        初始化MCP客户端
        
        Args:
            mcp_server_url: MCP服务器的URL，默认为"http://localhost:8000/mcp"
        """
        self.mcp_server_url = mcp_server_url
        self.client = Client(mcp_server_url)
    
    async def list_tools(self) -> Dict[str, Any]:
        """
        获取MCP服务器上所有可用的工具
        
        Returns:
            包含所有工具信息的字典
        """
        try:
            async with self.client:
                tools = await self.client.list_tools()
                print(tools)
                return {"tools": tools }
        except Exception as e:
            print(f"获取工具列表失败: {e}")
            return {"tools": []}
    
    async def call_tool(
        self, 
        tool_name: str, 
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        调用MCP服务器上的指定工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
        
        Returns:
            工具调用结果
        """
        try:
            async with self.client:
                result = await self.client.call_tool(tool_name, params or {})
                return result
        except Exception as e:
            print(f"调用工具 {tool_name} 失败: {e}")
            return {"error": str(e)}

if __name__ == '__main__':
    client = MCP_Client() 
    tools = asyncio.run(client.list_tools())
