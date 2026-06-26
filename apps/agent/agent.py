"""Dedicated BosesPH Agent running via MCP."""

import asyncio
import json
import os
import sys

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from prompts import SYSTEM_PROMPT


async def run_agent():
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in environment or .env file.")
        sys.exit(1)

    # Configure the MCP server connection to bosesph-mcp
    # We assume the agent is run within the same virtual environment, so `bosesph-mcp` is in PATH.
    server_params = StdioServerParameters(
        command="bosesph-mcp", args=[], env=os.environ.copy()
    )

    anthropic = AsyncAnthropic(api_key=api_key)

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Fetch tools from MCP server
            mcp_tools = await session.list_tools()

            # Convert MCP tools to Anthropic tool schema
            anthropic_tools = []
            for t in mcp_tools.tools:
                anthropic_tools.append(
                    {
                        "name": t.name,
                        "description": t.description,
                        "input_schema": t.inputSchema,
                    }
                )

            messages = [
                {"role": "user", "content": "Start the pipeline management run."}
            ]

            print("🚀 Starting BosesPH Agent Run...")

            # Simple agent loop (max 10 iterations)
            for _ in range(10):
                response = await anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2048,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                    tools=anthropic_tools,
                )

                # Append assistant's message
                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason == "tool_use":
                    tool_results = []
                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_args = content_block.input
                            print(
                                f"🛠️  Agent called tool: {tool_name}({json.dumps(tool_args)})"
                            )

                            try:
                                result = await session.call_tool(
                                    tool_name, arguments=tool_args
                                )
                                # result.content is a list of TextContent objects
                                result_text = "\n".join(
                                    c.text for c in result.content if c.type == "text"
                                )
                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "content": result_text,
                                    }
                                )
                            except Exception as e:
                                print(f"❌ Tool error: {e}")
                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "content": f"Error: {e}",
                                        "is_error": True,
                                    }
                                )

                    messages.append({"role": "user", "content": tool_results})
                else:
                    # Agent finished
                    print("✅ Agent run completed.")
                    for content_block in response.content:
                        if content_block.type == "text":
                            print(f"Agent says:\n{content_block.text}")
                    break


if __name__ == "__main__":
    asyncio.run(run_agent())
