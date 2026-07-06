[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Help,
    [switch]$SkipGlobalTool,
    [switch]$SkipFreeCADAddon,
    [switch]$SkipCalcEnv,
    [string[]]$Clients = @("ClaudeDesktop", "ClaudeCode", "Codex", "OpenCode", "Antigravity"),
    [string]$McpName = "freecad",
    [ValidateSet("xmlrpc", "socket", "embedded")]
    [string]$Mode = "xmlrpc",
    [string]$HostName = "localhost",
    [int]$XmlRpcPort = 9875,
    [int]$SocketPort = 9876,
    [int]$TimeoutMs = 30000,
    [string]$PackageVersion = "0.6.3",
    [switch]$InstallUvIfMissing,
    [string]$CalcPython = "3.12",
    [switch]$ForceConfig
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Show-Usage {
    @"
FreeCAD MCP quick installer

Usage:
  powershell -ExecutionPolicy Bypass -File .\install.ps1

Preview actions without writing:
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -WhatIf

Install only selected clients:
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -Clients Codex,ClaudeCode,OpenCode

Options:
  -SkipGlobalTool       Do not run uv tool install.
  -SkipFreeCADAddon     Do not copy the FreeCAD RobustMCPBridge workbench.
  -SkipCalcEnv          Do not build the calc toolkit venv (numpy<2 + pycufsm).
  -CalcPython           Python version for the calc venv. Default: 3.12 (numpy 1.26.4 has no 3.13 wheel).
  -Clients              ClaudeDesktop, ClaudeCode, Codex, OpenCode, Antigravity.
  -ForceConfig          Replace an existing client entry named "$McpName".
  -Mode                 xmlrpc, socket, or embedded. Default: xmlrpc.
  -PackageVersion       Version used when installing from a ZIP without git metadata.
  -InstallUvIfMissing   Install uv with Astral's official PowerShell installer if missing.
  -WhatIf               Show changes only.

Prerequisites:
  - Windows PowerShell or PowerShell 7.
  - uv installed and available on PATH, or pass -InstallUvIfMissing.
  - FreeCAD installed for using the workbench after setup.
"@
}

if ($Help) {
    Show-Usage
    exit 0
}

function Write-Step([string]$Message) {
    Write-Host "==> $Message"
}

function Write-Warn([string]$Message) {
    Write-Warning $Message
}

function Backup-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    $stamp = Get-Date -Format "yyyyMMddHHmmss"
    $backup = "$Path.bak-freecad-mcp-$stamp"
    if ($PSCmdlet.ShouldProcess($backup, "Create backup")) {
        Copy-Item -LiteralPath $Path -Destination $backup -Force
    }
    return $backup
}

function Ensure-Directory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        if ($PSCmdlet.ShouldProcess($Path, "Create directory")) {
            New-Item -ItemType Directory -Force -Path $Path | Out-Null
        }
    }
}

function Read-JsonOrEmpty([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        $raw = Get-Content -LiteralPath $Path -Raw
        if ($raw.Trim().Length -gt 0) {
            return $raw | ConvertFrom-Json
        }
    }
    return [pscustomobject]@{}
}

function Ensure-PropertyObject($Object, [string]$Name) {
    if (-not ($Object.PSObject.Properties.Name -contains $Name)) {
        $Object | Add-Member -MemberType NoteProperty -Name $Name -Value ([pscustomobject]@{})
    }
}

function Set-ObjectProperty($Object, [string]$Name, $Value) {
    if ($Object.PSObject.Properties.Name -contains $Name) {
        if (-not $ForceConfig) {
            Write-Warn "Entry '$Name' already exists. Keeping it. Use -ForceConfig to replace it."
            return $false
        }
        $Object.$Name = $Value
        return $true
    }
    else {
        $Object | Add-Member -MemberType NoteProperty -Name $Name -Value $Value
        return $true
    }
}

function Save-Json([string]$Path, $Object) {
    $dir = Split-Path -Parent $Path
    Ensure-Directory $dir
    Backup-File $Path | Out-Null
    if ($PSCmdlet.ShouldProcess($Path, "Write JSON config")) {
        $Object | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $Path -Encoding UTF8
    }
}

function New-McpEnv {
    [ordered]@{
        FREECAD_MODE = $Mode
        FREECAD_SOCKET_HOST = $HostName
        FREECAD_XMLRPC_PORT = [string]$XmlRpcPort
        FREECAD_SOCKET_PORT = [string]$SocketPort
        FREECAD_TIMEOUT_MS = [string]$TimeoutMs
        PYTHONIOENCODING = "utf-8"
    }
}

function New-ClaudeStyleServer([string]$CommandPath) {
    [pscustomobject]@{
        command = $CommandPath
        args = @()
        env = [pscustomobject](New-McpEnv)
    }
}

function Install-GlobalTool([string]$ServerRoot) {
    if ($SkipGlobalTool) {
        Write-Warn "Skipping global tool install."
        return
    }

    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) {
        if (-not $InstallUvIfMissing) {
            throw "uv was not found on PATH. Re-run with -InstallUvIfMissing or install uv first: https://docs.astral.sh/uv/getting-started/installation/"
        }

        Write-Step "Installing uv"
        if ($PSCmdlet.ShouldProcess("uv", "Install uv from https://astral.sh/uv/install.ps1")) {
            powershell -ExecutionPolicy Bypass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
            if ($LASTEXITCODE -ne 0) {
                throw "uv installer failed with exit code $LASTEXITCODE."
            }
        }

        $uv = Get-Command uv -ErrorAction SilentlyContinue
        if (-not $uv) {
            $candidate = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
            if (Test-Path -LiteralPath $candidate) {
                $uv = [pscustomobject]@{ Source = $candidate }
            }
        }
        if (-not $uv) {
            throw "uv install completed, but uv was not found. Open a new PowerShell window and rerun install.ps1."
        }
    }

    Write-Step "Installing freecad-mcp as a global uv tool"
    if ($PSCmdlet.ShouldProcess("freecad-mcp", "uv tool install --force")) {
        $oldGenericVersion = $env:SETUPTOOLS_SCM_PRETEND_VERSION
        $oldPackageVersion = $env:SETUPTOOLS_SCM_PRETEND_VERSION_FOR_FREECAD_ROBUST_MCP
        try {
            $env:SETUPTOOLS_SCM_PRETEND_VERSION = $PackageVersion
            $env:SETUPTOOLS_SCM_PRETEND_VERSION_FOR_FREECAD_ROBUST_MCP = $PackageVersion
            & $uv.Source tool install --force $ServerRoot
            if ($LASTEXITCODE -ne 0) {
                throw "uv tool install failed with exit code $LASTEXITCODE."
            }
        }
        finally {
            $env:SETUPTOOLS_SCM_PRETEND_VERSION = $oldGenericVersion
            $env:SETUPTOOLS_SCM_PRETEND_VERSION_FOR_FREECAD_ROBUST_MCP = $oldPackageVersion
        }
    }
}

function Get-FreecadMcpCommand {
    $cmd = Get-Command freecad-mcp -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $default = Join-Path $env:USERPROFILE ".local\bin\freecad-mcp.exe"
    if (Test-Path -LiteralPath $default) {
        return $default
    }

    throw "freecad-mcp executable was not found. Run without -SkipGlobalTool, or add it to PATH."
}

function Install-FreeCADWorkbench([string]$RepoRoot) {
    if ($SkipFreeCADAddon) {
        Write-Warn "Skipping FreeCAD workbench copy."
        return
    }

    $source = Join-Path $RepoRoot "freecad-addon-robust-mcp-server\freecad\RobustMCPBridge"
    if (-not (Test-Path -LiteralPath (Join-Path $source "init_gui.py"))) {
        throw "RobustMCPBridge source was not found at $source."
    }

    $freecadRoot = Join-Path $env:APPDATA "FreeCAD"
    $modDirs = New-Object System.Collections.Generic.List[string]
    $modDirs.Add((Join-Path $freecadRoot "Mod"))

    if (Test-Path -LiteralPath $freecadRoot) {
        Get-ChildItem -LiteralPath $freecadRoot -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "v*-*" } |
            ForEach-Object { $modDirs.Add((Join-Path $_.FullName "Mod")) }
    }

    $uniqueModDirs = $modDirs | Select-Object -Unique

    foreach ($modDir in $uniqueModDirs) {
        $targets = @(
            (Join-Path $modDir "RobustMCPBridge"),
            (Join-Path (Join-Path $modDir "freecad") "RobustMCPBridge")
        )

        foreach ($target in $targets) {
            Ensure-Directory (Split-Path -Parent $target)

            if (Test-Path -LiteralPath $target) {
                $backup = "$target.bak-freecad-mcp-$(Get-Date -Format yyyyMMddHHmmss)"
                if ($PSCmdlet.ShouldProcess($target, "Move existing workbench to backup")) {
                    Move-Item -LiteralPath $target -Destination $backup -Force
                }
            }

            Write-Step "Copying FreeCAD RobustMCPBridge workbench to $target"
            if ($PSCmdlet.ShouldProcess($target, "Copy workbench")) {
                Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
            }
        }
    }
}

function Resolve-Uv {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        return $uv.Source
    }
    $candidate = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (Test-Path -LiteralPath $candidate) {
        return $candidate
    }
    return $null
}

function Install-CalcEnv([string]$RepoRoot) {
    if ($SkipCalcEnv) {
        Write-Warn "Skipping calc toolkit venv."
        return
    }

    $pkg = Join-Path $RepoRoot "framework\galpao_fw"
    $req = Join-Path $pkg "requirements.txt"
    if (-not (Test-Path -LiteralPath $req)) {
        Write-Warn "requirements.txt not found at $req. Skipping calc env."
        return
    }

    $uv = Resolve-Uv
    if (-not $uv) {
        Write-Warn "uv not found; cannot build calc venv. Re-run with -InstallUvIfMissing or 'pip install -r `"$req`"' manually (needs numpy<2)."
        return
    }

    $venv = Join-Path $pkg ".venv"
    # numpy 1.26.4 ships wheels only up to cp312 -> pin the interpreter so uv does
    # not try to compile numpy from source (needs a C toolchain, and fails on 3.13).
    Write-Step "Building calc toolkit venv (Python $CalcPython, numpy<2 + pycufsm) at $venv"
    if ($PSCmdlet.ShouldProcess($venv, "uv venv + uv pip install -r requirements.txt")) {
        & $uv venv --python $CalcPython $venv
        if ($LASTEXITCODE -ne 0) {
            throw "uv venv failed with exit code $LASTEXITCODE."
        }
        $venvPython = Join-Path $venv "Scripts\python.exe"
        & $uv pip install --python $venvPython -r $req
        if ($LASTEXITCODE -ne 0) {
            throw "uv pip install (calc env) failed with exit code $LASTEXITCODE."
        }
        # Sanity: numpy<2 must hold for pycufsm.
        & $venvPython -c "import numpy,pycufsm,sys; v=numpy.__version__; sys.exit(0 if int(v.split('.')[0])<2 else 1)"
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "Calc venv built but numpy<2 / pycufsm check failed. Verify manually: `"$venvPython`" -c `"import numpy,pycufsm`""
        }
        else {
            Write-Step "Calc venv OK (numpy<2 + pycufsm import)"
        }
    }
}

function Configure-ClaudeDesktop([string]$CommandPath) {
    $path = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
    $config = Read-JsonOrEmpty $path
    Ensure-PropertyObject $config "mcpServers"
    $changed = Set-ObjectProperty $config.mcpServers $McpName (New-ClaudeStyleServer $CommandPath)
    if ($changed) {
        Save-Json $path $config
    }
}

function Configure-ClaudeCode([string]$CommandPath) {
    $claude = Get-Command claude -ErrorAction SilentlyContinue
    if (-not $claude) {
        Write-Warn "Claude Code CLI was not found. Skipping ClaudeCode."
        return
    }

    $envArgs = @()
    foreach ($entry in (New-McpEnv).GetEnumerator()) {
        $envArgs += @("-e", "$($entry.Key)=$($entry.Value)")
    }

    Write-Step "Registering Claude Code MCP server"
    if ($PSCmdlet.ShouldProcess("Claude Code user config", "claude mcp add")) {
        & $claude.Source mcp add -s user $McpName @envArgs -- $CommandPath
        if ($LASTEXITCODE -ne 0) {
            throw "claude mcp add failed with exit code $LASTEXITCODE."
        }
    }
}

function Remove-TomlSection([string]$Content, [string[]]$Sections) {
    $lines = $Content -split "`r?`n"
    $out = New-Object System.Collections.Generic.List[string]
    $skip = $false
    foreach ($line in $lines) {
        if ($line -match '^\s*\[(.+?)\]\s*$') {
            $section = $Matches[1]
            $skip = $Sections -contains $section
        }
        if (-not $skip) {
            $out.Add($line)
        }
    }
    return ($out -join [Environment]::NewLine).TrimEnd()
}

function Configure-Codex([string]$CommandPath) {
    $dir = Join-Path $env:USERPROFILE ".codex"
    $path = Join-Path $dir "config.toml"
    Ensure-Directory $dir
    $content = ""
    if (Test-Path -LiteralPath $path) {
        $content = Get-Content -LiteralPath $path -Raw
    }

    if (($content -match "(?m)^\[mcp_servers\.$([regex]::Escape($McpName))\]") -and (-not $ForceConfig)) {
        Write-Warn "Codex MCP '$McpName' already exists. Use -ForceConfig to replace it."
        return
    }

    Backup-File $path | Out-Null
    $content = Remove-TomlSection $content @("mcp_servers.$McpName", "mcp_servers.$McpName.env")
    $block = @"

[mcp_servers.$McpName]
command = '$CommandPath'
args = []
startup_timeout_sec = 60
tool_timeout_sec = 300
enabled = true

[mcp_servers.$McpName.env]
FREECAD_MODE = '$Mode'
FREECAD_SOCKET_HOST = '$HostName'
FREECAD_XMLRPC_PORT = '$XmlRpcPort'
FREECAD_SOCKET_PORT = '$SocketPort'
FREECAD_TIMEOUT_MS = '$TimeoutMs'
PYTHONIOENCODING = 'utf-8'
"@

    if ($PSCmdlet.ShouldProcess($path, "Write Codex config")) {
        ($content.TrimEnd() + [Environment]::NewLine + $block.TrimStart() + [Environment]::NewLine) |
            Set-Content -LiteralPath $path -Encoding UTF8
    }
}

function Configure-OpenCode([string]$CommandPath) {
    $dir = Join-Path $env:USERPROFILE ".config\opencode"
    $path = Join-Path $dir "opencode.json"
    $config = Read-JsonOrEmpty $path
    if (-not ($config.PSObject.Properties.Name -contains '$schema')) {
        $config | Add-Member -MemberType NoteProperty -Name '$schema' -Value "https://opencode.ai/config.json"
    }
    Ensure-PropertyObject $config "mcp"
    $server = [pscustomobject]@{
        type = "local"
        command = @($CommandPath)
        enabled = $true
        timeout = 300000
        environment = [pscustomobject](New-McpEnv)
    }
    $changed = Set-ObjectProperty $config.mcp $McpName $server
    if ($changed) {
        Save-Json $path $config
    }
}

function Configure-Antigravity([string]$CommandPath) {
    $dir = Join-Path $env:APPDATA "Antigravity IDE\User"
    $path = Join-Path $dir "mcp.json"
    $config = Read-JsonOrEmpty $path
    Ensure-PropertyObject $config "servers"
    $server = [pscustomobject]@{
        type = "stdio"
        command = $CommandPath
        args = @()
        env = [pscustomobject](New-McpEnv)
    }
    $changed = Set-ObjectProperty $config.servers $McpName $server
    if ($changed) {
        Save-Json $path $config
    }
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$serverRoot = Join-Path $repoRoot "freecad-addon-robust-mcp-server"
if (-not (Test-Path -LiteralPath (Join-Path $serverRoot "pyproject.toml"))) {
    throw "Expected vendored server at $serverRoot. Download the full repository ZIP, not only install.ps1."
}

Write-Step "FreeCAD MCP installer starting"
Install-GlobalTool $serverRoot
$commandPath = Get-FreecadMcpCommand
Install-FreeCADWorkbench $repoRoot
Install-CalcEnv $repoRoot

foreach ($client in $Clients) {
    switch ($client.ToLowerInvariant()) {
        "claudedesktop" { Configure-ClaudeDesktop $commandPath }
        "claudecode" { Configure-ClaudeCode $commandPath }
        "codex" { Configure-Codex $commandPath }
        "opencode" { Configure-OpenCode $commandPath }
        "antigravity" { Configure-Antigravity $commandPath }
        default { Write-Warn "Unknown client '$client'. Skipping." }
    }
}

Write-Step "Done"
Write-Host "MCP command: $commandPath"
Write-Host "Next: restart your AI clients, then open FreeCAD."
Write-Host "The Robust MCP Bridge auto-starts ~3s after FreeCAD launch (ports $XmlRpcPort / $SocketPort)."
Write-Host "Verify: freecad-mcp --check --mode $Mode --host $HostName --port $XmlRpcPort"
if (-not $SkipCalcEnv) {
    Write-Host "Calc toolkit venv: framework\galpao_fw\.venv (numpy<2 + pycufsm)."
    Write-Host "Run calc with: framework\galpao_fw\.venv\Scripts\python.exe (see skills\build-warehouse\QUICKSTART.md)."
}
