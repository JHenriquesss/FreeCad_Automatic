# FreeCAD Automatic MCP Installer

This repository is a portable Windows installer for the FreeCAD Robust MCP
server and bridge.

Goal: download the GitHub ZIP on a new PC, run one PowerShell command, then use
FreeCAD from Codex, Claude Desktop, Claude Code, OpenCode, and Antigravity.

## What It Installs

- Global `freecad-mcp` command via `uv tool install`.
- FreeCAD `RobustMCPBridge` workbench under FreeCAD's `Mod\freecad`
  namespace folder and the classic direct `Mod\RobustMCPBridge` folder,
  including versioned FreeCAD profile folders when present.
- MCP client entries for:
  - Claude Desktop
  - Claude Code
  - Codex
  - OpenCode
  - Antigravity IDE

The vendored server lives in:

```text
freecad-addon-robust-mcp-server/
```

## Quick Install From ZIP

1. Download this repository as a ZIP from GitHub.
2. Extract it somewhere simple, for example:

```text
C:\Tools\FreeCad_Automatic
```

3. Open PowerShell in that folder.
4. Preview the installation:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -WhatIf
```

5. Run the installation. This variant installs `uv` first if the PC does not
   already have it:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -InstallUvIfMissing
```

6. Restart your AI clients.
7. Open FreeCAD, select `Robust MCP Bridge`, then start the bridge.

## Prerequisites

- Windows.
- FreeCAD installed.
- `uv` installed and available in PATH, or use `-InstallUvIfMissing`.
- Internet access for the first install, because `uv` downloads Python packages.

Install `uv`:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Or let this installer do it:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -InstallUvIfMissing
```

## Useful Commands

Show installer help:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Help
```

Install only Codex and Claude Code:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Clients Codex,ClaudeCode
```

Replace existing MCP entries:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -ForceConfig
```

Skip copying the FreeCAD workbench:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -SkipFreeCADAddon
```

## Connection Test

After FreeCAD is open and the bridge is running:

```powershell
Test-NetConnection localhost -Port 9875
freecad-mcp --check --mode xmlrpc --host localhost --port 9875
```

In an AI client, ask:

```text
Use the freecad MCP server and call get_connection_status, get_freecad_version,
and get_active_document.
```

## Default MCP Settings

The installer writes these defaults:

```text
FREECAD_MODE=xmlrpc
FREECAD_SOCKET_HOST=localhost
FREECAD_XMLRPC_PORT=9875
FREECAD_SOCKET_PORT=9876
FREECAD_TIMEOUT_MS=30000
PYTHONIOENCODING=utf-8
```

## Files Modified On The Target PC

The installer creates backups before writing existing config files.

Typical paths:

```text
%APPDATA%\Claude\claude_desktop_config.json
%USERPROFILE%\.claude.json
%USERPROFILE%\.codex\config.toml
%USERPROFILE%\.config\opencode\opencode.json
%APPDATA%\Antigravity IDE\User\mcp.json
%APPDATA%\FreeCAD\Mod\RobustMCPBridge
%APPDATA%\FreeCAD\Mod\freecad\RobustMCPBridge
%APPDATA%\FreeCAD\v1-1\Mod\RobustMCPBridge
%APPDATA%\FreeCAD\v1-1\Mod\freecad\RobustMCPBridge
```

## Notes

- If a client is not installed, its step is skipped or its config is created.
- Claude Code is configured through `claude mcp add` when the CLI exists.
- Antigravity support uses the VS Code-style `User\mcp.json` file.
- The MCP health check fails until FreeCAD is open and the Robust MCP Bridge is
  listening. In FreeCAD, switch to `Robust MCP Bridge` and click `Start MCP
  Bridge`, or enable auto-start in the workbench preferences.
