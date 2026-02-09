# NeuroResolv MCP Server (Integrated)

NeuroResolv now supports the Model Context Protocol (MCP) directly via our FastAPI backend. This allows any MCP-compatible client (like `gemini cli`, Cursor, or Claude Desktop) to connect using the SSE transport.

## Features

- **List Resolutions**: View all your active goals and resolutions.
- **Weekly Focus**: Get your aggregated weekly focus and micro-actions.
- **Get Milestones**: See the roadmap and milestones for a specific resolution.
- **Check-in**: Log text-only progress updates.

## Configuration (SSE)

The MCP server is hosted at: `http://localhost:8000/mcp/sse` (Local) or `https://neuroresolv-api.ffinity.com/mcp/sse` (Production).
> Production is currently under development. Please try local one.

### Authentication

Clients **must** provide a Bearer token in the `Authorization` header during the initial connection.

**How to get your token:**
1. Login to the NeuroResolv web app.
2. Open Browser DevTools -> Application -> Local Storage. Copy the value of the `token` key.
3. Or, go to "Network" tab in Browser DevTools, click on `login` API request, click on "Response" tab and copy the value of the `access_token` key.
Sample `Response`:
```json
{
    "access_token": "eyJhbGciOiJIUzdfdfdfdfdfdfdfdsdsdVCJ9.eyJzsdsdsdsdsdsdXhwIjoxNzcwNzAyNTQ3fQ.7RrfZaYrC5t45qhOU6wbbP7NWzwQHSRUGmaPWAQwyMM",
    "token_type": "bearer",
    "user": {
        "id": 1,
        "email": "john@doe.com",
        "full_name": "john",
        "is_active": true,
        "created_at": "2026-02-04T15:44:49.879986"
    }
}
```

## Usage with Gemini CLI

To use this with `gemini cli`, configure it to use the SSE endpoint:

```bash
# Add the NeuroResolv LOCAL MCP server
gemini mcp add neuroresolv --type sse http://localhost:8000/mcp/sse --header "Authorization: Bearer YOUR_TOKEN_HERE"

# Add the NeuroResolv PRODUCTION MCP server (Production is currently under development.)
gemini mcp add neuroresolv --type sse https://neuroresolv-api.ffinity.com/mcp/sse --header "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Usage with Other Clients

- **Cursor**: Go to Settings -> MCP -> Add New Server. Choice: `SSE`. URL: `https://neuroresolv-api.ffinity.com/mcp/sse`.
- **Claude Desktop**: Edit your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "neuroresolv": {
      "url": "https://neuroresolv-api.ffinity.com/mcp/sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```
