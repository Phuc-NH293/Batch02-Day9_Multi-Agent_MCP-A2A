$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$LogDir = Join-Path $Root "logs"

if (-not (Test-Path $Python)) {
    $Python = "python"
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$Processes = @()

function Start-AgentProcess {
    param(
        [string] $Name,
        [string] $Module,
        [int] $Port
    )

    $SafeName = $Name.ToLower().Replace(" ", "_")
    $StdOut = Join-Path $LogDir "$SafeName.out.log"
    $StdErr = Join-Path $LogDir "$SafeName.err.log"

    Write-Host "Starting $Name on port $Port..."
    $process = Start-Process `
        -FilePath $Python `
        -ArgumentList "-m", $Module `
        -WorkingDirectory $Root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $StdOut `
        -RedirectStandardError $StdErr `
        -PassThru

    return [pscustomobject]@{
        Name = $Name
        Module = $Module
        Port = $Port
        Process = $process
        StdOut = $StdOut
        StdErr = $StdErr
    }
}

function Show-ServiceFailure {
    param($Service)

    Write-Host ""
    Write-Host "$($Service.Name) stopped unexpectedly."
    Write-Host "Stdout log: $($Service.StdOut)"
    Write-Host "Stderr log: $($Service.StdErr)"

    if (Test-Path $Service.StdErr) {
        Write-Host ""
        Write-Host "Last stderr lines:"
        Get-Content -LiteralPath $Service.StdErr -Tail 20
    }
}

try {
    $Processes += Start-AgentProcess -Name "Registry" -Module "registry" -Port 10000
    Start-Sleep -Seconds 2

    $Processes += Start-AgentProcess -Name "Tax Agent" -Module "tax_agent" -Port 10102
    $Processes += Start-AgentProcess -Name "Compliance Agent" -Module "compliance_agent" -Port 10103
    Start-Sleep -Seconds 3

    $Processes += Start-AgentProcess -Name "Law Agent" -Module "law_agent" -Port 10101
    Start-Sleep -Seconds 3

    $Processes += Start-AgentProcess -Name "Customer Agent" -Module "customer_agent" -Port 10100

    Write-Host ""
    Write-Host "All services started:"
    Write-Host "  Registry:         http://localhost:10000"
    Write-Host "  Customer Agent:   http://localhost:10100"
    Write-Host "  Law Agent:        http://localhost:10101"
    Write-Host "  Tax Agent:        http://localhost:10102"
    Write-Host "  Compliance Agent: http://localhost:10103"
    Write-Host ""
    Write-Host "Logs are in:"
    Write-Host "  $LogDir"
    Write-Host ""
    Write-Host "Run this in another PowerShell window:"
    Write-Host "  uv run python test_client.py"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all services."

    while ($true) {
        Start-Sleep -Seconds 2
        foreach ($service in $Processes) {
            $service.Process.Refresh()
            if ($service.Process.HasExited) {
                Show-ServiceFailure -Service $service
                throw "One or more services stopped unexpectedly."
            }
        }
    }
}
finally {
    if ($Processes.Count -gt 0) {
        Write-Host ""
        Write-Host "Stopping services..."
        foreach ($service in $Processes) {
            try {
                $service.Process.Refresh()
                if (-not $service.Process.HasExited) {
                    Stop-Process -Id $service.Process.Id -Force -ErrorAction SilentlyContinue
                }
            }
            catch {
                Write-Host "Could not stop $($service.Name): $($_.Exception.Message)"
            }
        }
    }
}
