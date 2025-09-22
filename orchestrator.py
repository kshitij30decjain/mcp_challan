# main.py
import asyncio
import json

import fastapi
import openai
from pydantic import BaseModel
from fastmcp import Client
from fastmcp.client.transports import SSETransport

client_openai = openai.AsyncOpenAI(api_key="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")



app = fastapi.FastAPI(title="MCP Tool Orchestrator")

MCP_SERVERS = {}
transport = SSETransport(
    url="http://localhost:8034/sse",
    headers={"Authorization": "Bearer token"}
)
client = Client(transport)

# Request model for the API
class UserRequest(BaseModel):
    user_prompt: str

async def discover_tools_for_server():
    """
    Connect to one MCP server and return a list of tool descriptors.
    Each descriptor is converted to a simple dict so it's JSON-serializable.
    """
    simplified = []
    async with client:
        tools = await client.list_tools()

        for tool in tools:
            tool_record = {
                "tool_name": tool.name,
                "tool_description": tool.description,
                "tool_arguments": tool.inputSchema if tool.inputSchema else {}
            }
            simplified.append(tool_record)
        return simplified

async def call_tool_on_server( tool_name, arguments):
    """
    Call a named tool on a specific MCP server and return the result.
    """
   # async with Client(server_source) as mcp_client:
        # call_tool returns a CallToolResult-like object (or raises)
    async with client:
        result = await client.call_tool(tool_name, arguments)
    return result

@app.post("/process-request")
async def process_request(request: UserRequest):
    user_prompt = request.user_prompt

    # 1. DYNAMIC DISCOVERY: Get tools from ALL configured servers
    all_tools = []

    try:
        tools_json_str = await discover_tools_for_server()
        json_str = json.dumps(tools_json_str)
    except Exception as e:
            print(f"Warning: Could not connect to server : {e}")




    # 2. FIRST LLM CALL: Let the LLM choose from ALL available tools
    decision_prompt = f"""
    USER REQUEST: "{user_prompt}"

    AVAILABLE TOOLS:
    {json_str}

    Analyze the user's request. Choose the single most appropriate tool to call first.
    Output ONLY a JSON object with this structure:
    {{
      "tool": "exact_tool_name",
      "server": "server_name",
      "arguments": {{
        "arg1": value1,
        "arg2": value2
         }}
        }}
"""
    decision_completion = await client_openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": decision_prompt}],
        response_format={"type": "json_object"}
    )

    decision = json.loads(decision_completion.choices[0].message.content)
    chosen_tool_name = decision["tool"]
    chosen_server = decision["server"]
    tool_arguments = decision.get("arguments", {})

    # 3. Find the server source for the chosen tool
    if chosen_server not in MCP_SERVERS:
        print(f"Error: LLM selected server '{chosen_server}' which is not configured.")
       # return
    #server_source = MCP_SERVERS[chosen_server]


    # 4. Execute the chosen tool using fastMCP client
    try:
        tool_result = await call_tool_on_server( chosen_tool_name, tool_arguments)
    except Exception as e:
        tool_result = f"Error while calling tool: {e}"

    # 5. SECOND LLM CALL: Formulate the final answer
    final_prompt = f"""
User asked: "{user_prompt}"

I used the tool '{chosen_tool_name}' ' with arguments {tool_arguments}.
The tool returned: "{tool_result}"

Please provide a helpful final answer for the user.
"""
    final_completion = await client_openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": final_prompt}]
    )
    final_response = final_completion.choices[0].message.content

    print(f"\nAnswer: {final_response}")
    return {"response": final_response}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "MCP Tool Orchestrator"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
