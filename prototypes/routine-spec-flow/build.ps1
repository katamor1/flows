param(
    [Parameter(Mandatory = $true)]
    [string] $PythonExe,
    [switch] $Verify
)
$ErrorActionPreference = 'Stop'
$flowScript = Join-Path $PSScriptRoot 'tools/flow.py'
& $PythonExe $flowScript validate
if ($LASTEXITCODE -ne 0) { throw 'Source validation failed' }
& $PythonExe $flowScript build
if ($LASTEXITCODE -ne 0) { throw 'Document generation failed' }
if ($Verify) {
    & $PythonExe (Join-Path $PSScriptRoot 'tools/verify_flow.py')
    if ($LASTEXITCODE -ne 0) { throw 'Flow verification failed' }
}
