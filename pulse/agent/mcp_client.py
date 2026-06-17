import os
import sys
import logging
import asyncio
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

logger = logging.getLogger("pulse-mcp-client")

class MCPClient:
    def __init__(self, command: str, args: list[str], env: dict = None):
        self.command = command
        self.args = args
        self.env = env or os.environ.copy()
        self.session = None
        self.read = None
        self.write = None
        self._ctx = None

    async def connect(self):
        logger.info(f"Connecting to MCP Server: {self.command} {' '.join(self.args)}...")
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env
        )
        
        self._ctx = stdio_client(server_params)
        self.read, self.write = await self._ctx.__aenter__()
        self.session = ClientSession(self.read, self.write)
        await self.session.__aenter__()
        await self.session.initialize()
        logger.info("MCP Server initialized successfully.")

    async def disconnect(self):
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error exiting session: {e}")
        if self._ctx:
            try:
                await self._ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error exiting stdio context: {e}")
        logger.info("Disconnected from MCP Server.")

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Calls a tool by name on the MCP server and returns the parsed result."""
        if not self.session:
            raise RuntimeError("Not connected to MCP Server.")
        
        logger.info(f"Calling tool '{name}' with arguments: {arguments}")
        result = await self.session.call_tool(name, arguments)
        
        # Parse result contents (usually TextContent containing JSON string or plain text)
        if not result.content:
            return {}
            
        content_text = result.content[0].text
        try:
            # Check if output is a JSON string
            return json.loads(content_text)
        except (json.JSONDecodeError, TypeError):
            # Fallback to plain string wrapped in dict
            return {"raw_output": content_text}
