---
description: Connect the MarketCheck MCP server for this plugin
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
argument-hint: [api-key]
---

Set up MarketCheck MCP connection. No npm packages or local processes required.

## Step 0: Check if already connected

If `mcp__marketcheck__*` tools are available: "MarketCheck MCP already connected. No setup needed." Stop.

## Step 1: Collect API Key

Use $ARGUMENTS as API key if provided. Otherwise ask: "Enter your MarketCheck API key (get one at https://www.marketcheck.com)"

## Step 2: Find config file

Check in order: `~/.claude/.mcp.json` (user-level), `.mcp.json` (project-level). Read whichever exists. If neither, create `~/.claude/.mcp.json`.

## Step 3: Write MCP config

Merge into existing config (preserve other servers):
```json
{ "mcpServers": { "marketcheck": { "type": "url", "url": "https://mc-api.marketcheck.com/mcp?api_key=THE_API_KEY" } } }
```

## Step 4: Confirm

Tell user MCP is configured. Show server URL and config path. Emphasize: **restart Claude Code** for MCP to connect.

Next steps:
1. Restart Claude Code
2. Run `/auction-house:onboarding` to set up your profile
3. Try: "What's selling in Texas?" — DMA market overview
