# Bitbucket MCP

A FastMCP server for Bitbucket Cloud REST API.

## Features

- List repositories
- Get repo details
- List branches
- List pull requests
- Create/manage pull requests
- And more...

## Setup

### 1. Create a Bitbucket API Token

1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Name it something like "MCP Tool"
4. Copy the token

### 2. Set Environment Variables

```bash
export BITBUCKET_EMAIL="your-email@domain.com"
export BITBUCKET_API_TOKEN="your-api-token-here"
```

Or create a `.env` file:

```bash
BITBUCKET_EMAIL=your-email@domain.com
BITBUCKET_API_TOKEN=your-api-token-here
```

### 3. Run the Server

```bash
# Using uv (recommended)
uv run --directory /path/to/bitbucket-mcp python server.py

# Or with pip
pip install -r requirements.txt
python server.py
```

### 4. Connect via mcporter

Add to your `mcporter.json`:

```json
{
  "mcpServers": {
    "bitbucket": {
      "command": "/path/to/uv",
      "args": [
        "run",
        "--directory",
        "/path/to/bitbucket-mcp",
        "python",
        "server.py"
      ],
      "env": {
        "BITBUCKET_EMAIL": "your-email@domain.com",
        "BITBUCKET_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

## Requirements

- Python 3.10+
- `uv` (optional, but recommended)

## License

MIT
