# QA entrypoint only. Does not build, run launcher unit tests, publish, or alter pack files.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$LauncherRoot,
    [ValidateSet('Runtime', 'Migration')][string]$Tool = 'Runtime',
    [ValidateSet('Debug', 'Release')][string]$Configuration = 'Debug',
    [Parameter(Mandatory = $true)][string[]]$RunnerArguments
)
$ErrorActionPreference = 'Stop'
$launcher = [IO.Path]::GetFullPath($LauncherRoot)
if (-not (Test-Path -LiteralPath (Join-Path $launcher 'Program/Minecraft.csproj') -PathType Leaf)) {
    throw 'LauncherRoot must select the reviewed LANMinecraft source checkout.'
}
$name = if ($Tool -eq 'Runtime') { 'ForgeRuntimeQa' } else { 'PackMigrationQa' }
$assembly = Join-Path $launcher "tools/$name/bin/$Configuration/net10.0-windows/win-x64/$name.dll"
if (-not (Test-Path -LiteralPath $assembly -PathType Leaf)) {
    throw "Build only tools/$name in the selected launcher checkout before using this explicit QA entrypoint."
}
$contract = Join-Path $PSScriptRoot 'launcher-runtime-contract.json'
& dotnet $assembly @RunnerArguments --contract $contract
if ($LASTEXITCODE -ne 0) { throw "The selected pack QA runner failed with exit code $LASTEXITCODE." }
