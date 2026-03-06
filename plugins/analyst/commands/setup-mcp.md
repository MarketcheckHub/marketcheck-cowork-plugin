---
description: Connect the MarketCheck MCP server for the analyst plugin
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
argument-hint: [api-key]
---

Set up the MarketCheck MCP connection so all analyst plugin skills and commands can access automotive market data. Connects directly to MarketCheck's hosted MCP server -- no npm packages or local processes required.

## Step 0: Check if already connected

Check if `mcp__marketcheck__*` tools are available in the current session. If the tools exist, tell the user:

"The MarketCheck MCP is already connected and working. No setup needed."

Then stop.

## Step 1: Collect API Key

Ask the user for their MarketCheck API key:
- If $ARGUMENTS contains a value, use it as the API key
- Otherwise ask: "Enter your MarketCheck API key (get one at https://www.marketcheck.com)"

## Step 2: Determine config location

Check which MCP config files exist, in order of preference:

1. `~/.claude/.mcp.json` -- user-level Claude Code config
2. `.mcp.json` in the current project root -- project-level config

Read whichever exists. If neither exists, create `~/.claude/.mcp.json`.

## Step 3: Write the MCP config

Merge the `marketcheck` server into the existing config (preserve any other MCP servers already configured):

```json
{
  "mcpServers": {
    "marketcheck": {
      "type": "url",
      "url": "https://mc-api.marketcheck.com/mcp?api_key=THE_API_KEY_FROM_STEP_1"
    }
  }
}
```

**Important**: If the file already has other `mcpServers` entries, preserve them -- only add or update the `marketcheck` entry.

## Step 4: Confirm & next steps

Tell the user:

```
MarketCheck MCP configured successfully.

Server: https://mc-api.marketcheck.com/mcp
Config: [file path where it was written]

Next steps:
1. Restart Claude Code for the MCP to connect
2. Run /onboarding to set up your analyst profile
3. Try: "How is Ford doing?" for an OEM investment signal
4. Try: "Monthly auto market report" for sector-wide intelligence
```

**Important**: The MCP will NOT connect until Claude Code is restarted. Make this clear to the user.
