# Brevo Service Runner for Windows (PowerShell)
# Usage: .\run_service.ps1 [start|stop|status|logs|install|uninstall]

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "install", "uninstall", "help")]
    [string]$Action = "help"
)

$ServiceName = "brevo-service"
$ApiPort = 8010
$BackgroundService = "brevo.background_service"
$ApiService = "brevo.main:app"

$Red = [System.ConsoleColor]::Red
$Green = [System.ConsoleColor]::Green
$Yellow = [System.ConsoleColor]::Yellow
$Blue = [System.ConsoleColor]::Blue

function Write-ColorOutput($Message, $Color = [System.ConsoleColor]::White) {
    Write-Host $Message -ForegroundColor $Color
}

function Test-ProcessRunning($ProcessId) {
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

function Get-ServicePID($ServiceType) {
    $pidFile = "$ServiceType.pid"
    if (Test-Path $pidFile) {
        try {
            $processId = [int](Get-Content $pidFile -Raw).Trim()
            if (Test-ProcessRunning $processId) {
                return $processId
            }
        }
        catch {
            # Invalid PID file
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
    return $null
}

function Test-ServiceRunning($ServiceName) {
    $processId = Get-ServicePID $ServiceName
    return $processId -ne $null
}

function Stop-Service($ServiceName) {
    $pidFile = "$ServiceName.pid"
    
    if (Test-Path $pidFile) {
        try {
            $processId = [int](Get-Content $pidFile -Raw).Trim()
            if (Test-ProcessRunning $processId) {
                Write-ColorOutput "Stopping $ServiceName (PID: $processId)..." $Yellow
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2
            }
        }
        catch {
            # Process might already be dead
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
    
    # Also kill any lingering processes by name
    if ($ServiceName -eq "api_service") {
        Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -like "*uvicorn*brevo.main*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    }
    elseif ($ServiceName -eq "background_service") {
        Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -like "*brevo.background_service*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    }
}

function Start-Services {
    Write-ColorOutput "Starting Brevo Services..." $Blue
    
    # Check if services are already running
    if (Test-ServiceRunning "api_service") {
        Write-ColorOutput "WARNING: API service is already running. Stopping it first..." $Yellow
        Stop-Service "api_service"
    }
    
    
    if (Test-ServiceRunning "background_service") {
        Write-ColorOutput "WARNING: Background service is already running. Stopping it first..." $Yellow
        Stop-Service "background_service"
    }
    
    # Check if .env exists
    if (-not (Test-Path ".env")) {
        Write-ColorOutput "Warning: .env file not found. Please create one with BREVO_API_KEY" $Yellow
    }
    
    # Check if virtual environment is activated
    if (-not $env:VIRTUAL_ENV) {
        Write-ColorOutput "Tip: Consider activating your virtual environment first" $Yellow
    }
    
    # Start API service
    Write-ColorOutput "Starting API service on port $ApiPort..." $Green
    $apiProcess = Start-Process -FilePath "uvicorn" -ArgumentList "$ApiService", "--host", "0.0.0.0", "--port", "$ApiPort", "--reload" -RedirectStandardOutput "api_service.log" -RedirectStandardError "api_service_error.log" -WindowStyle Hidden -PassThru
    $apiProcess.Id | Out-File -FilePath "api_service.pid" -Encoding UTF8
    
    Start-Sleep -Seconds 2
    
    # Start background service
    Write-ColorOutput "Starting background service..." $Green
    $bgProcess = Start-Process -FilePath "python" -ArgumentList "-m", "$BackgroundService" -RedirectStandardOutput "background_service.log" -RedirectStandardError "background_service_error.log" -WindowStyle Hidden -PassThru
    $bgProcess.Id | Out-File -FilePath "background_service.pid" -Encoding UTF8
    
    Write-ColorOutput "Services started successfully!" $Green
    Write-ColorOutput "   Log viewer: http://localhost:$ApiPort" $Blue
    Write-ColorOutput "   API docs: http://localhost:$ApiPort/docs" $Blue
    Write-ColorOutput "   API PID: $($apiProcess.Id)" $Blue
    Write-ColorOutput "   Background PID: $($bgProcess.Id)" $Blue
    
    $openBrowser = Read-Host "Open log viewer in browser? [y/N]"
    if ($openBrowser -eq "y" -or $openBrowser -eq "Y") {
        try {
            Start-Process cmd -ArgumentList "/c", "start", "http://localhost:$ApiPort" -WindowStyle Hidden
        }
        catch {
            Write-ColorOutput "Could not open browser automatically. Please visit: http://localhost:$ApiPort" $Yellow
        }
    }
}

function Stop-Services {
    Write-ColorOutput "Stopping Brevo Services..." $Yellow
    
    Stop-Service "api_service"
    Stop-Service "background_service"
    
    Write-ColorOutput "All services stopped" $Green
}

function Show-Status {
    Write-ColorOutput "Brevo Service Status:" $Blue
    
    # Check API service
    if (Test-ServiceRunning "api_service") {
        $apiProcessId = Get-ServicePID "api_service"
        Write-ColorOutput "   API Service: Running (PID: $apiProcessId)" $Green
    } else {
        Write-ColorOutput "   API Service: Not running" $Red
    }
    
    # Check background service
    if (Test-ServiceRunning "background_service") {
        $bgProcessId = Get-ServicePID "background_service"
        Write-ColorOutput "   Background Service: Running (PID: $bgProcessId)" $Green
    } else {
        Write-ColorOutput "   Background Service: Not running" $Red
    }
    
    # Check for any lingering processes
    Write-Output ""
    Write-ColorOutput "Process Analysis:" $Blue
    $brevoProcesses = @(Get-Process | Where-Object { 
        ($_.ProcessName -eq "python" -and ($_.CommandLine -like "*uvicorn*brevo*" -or $_.CommandLine -like "*brevo.background_service*")) -or
        ($_.ProcessName -eq "uvicorn" -and $_.CommandLine -like "*brevo*")
    })
    
    if ($brevoProcesses.Count -gt 0) {
        Write-ColorOutput "   Total Brevo-related processes: $($brevoProcesses.Count)" $Blue
        if ($brevoProcesses.Count -gt 2) {
            Write-ColorOutput "   WARNING: Multiple processes detected. Consider running stop first." $Yellow
        }
    } else {
        Write-ColorOutput "   No Brevo processes found" $Blue
    }
    
    Write-ColorOutput "   Log viewer: http://localhost:$ApiPort" $Blue
    
    # Show system info
    $memory = [math]::Round((Get-Process python -ErrorAction SilentlyContinue | Measure-Object WorkingSet -Sum).Sum / 1MB, 2)
    if ($memory -gt 0) {
        Write-ColorOutput "   Python Memory Usage: ${memory}MB" $Blue
    }
}

function Restart-Services {
    Write-ColorOutput "Restarting Brevo Services..." $Blue
    
    # Stop services
    Stop-Service "api_service"
    Stop-Service "background_service"
    
    Start-Sleep -Seconds 2
    
    # Check if .env exists
    if (-not (Test-Path ".env")) {
        Write-ColorOutput "Warning: .env file not found. Please create one with BREVO_API_KEY" $Yellow
    }
    
    # Start services
    Write-ColorOutput "Starting API service on port $ApiPort..." $Green
    $apiProcess = Start-Process -FilePath "uvicorn" -ArgumentList "$ApiService", "--host", "0.0.0.0", "--port", "$ApiPort", "--reload" -RedirectStandardOutput "api_service.log" -RedirectStandardError "api_service_error.log" -WindowStyle Hidden -PassThru
    $apiProcess.Id | Out-File -FilePath "api_service.pid" -Encoding UTF8
    
    Write-ColorOutput "Starting background service..." $Green
    $bgProcess = Start-Process -FilePath "python" -ArgumentList "-m", "$BackgroundService" -RedirectStandardOutput "background_service.log" -RedirectStandardError "background_service_error.log" -WindowStyle Hidden -PassThru
    $bgProcess.Id | Out-File -FilePath "background_service.pid" -Encoding UTF8
    
    Write-ColorOutput "Services restarted successfully!" $Green
    Write-ColorOutput "   Log viewer: http://localhost:$ApiPort" $Blue
    Write-ColorOutput "   API docs: http://localhost:$ApiPort/docs" $Blue
    Write-ColorOutput "   API PID: $($apiProcess.Id)" $Blue
    Write-ColorOutput "   Background PID: $($bgProcess.Id)" $Blue
}

function Show-Logs {
    Write-ColorOutput "Viewing service logs (Ctrl+C to exit)..." $Blue
    
    $logFiles = @("api_service.log", "background_service.log", "brevo_service.log") | Where-Object { Test-Path $_ }
    
    if ($logFiles.Count -eq 0) {
        Write-ColorOutput "No log files found yet" $Yellow
        return
    }
    
    try {
        Get-Content $logFiles -Wait
    }
    catch {
        Write-ColorOutput "Error reading log files: $($_.Exception.Message)" $Red
    }
}

function Install-Service {
    Write-ColorOutput "📦 Installing Brevo Service as Windows Service..." $Blue
    
    # Check if running as administrator
    if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
        Write-ColorOutput "❌ This operation requires administrator privileges" $Red
        Write-ColorOutput "Please run PowerShell as Administrator and try again" $Yellow
        return
    }
    
    # Install as Windows Service using NSSM (if available) or create scheduled task
    if (Get-Command nssm -ErrorAction SilentlyContinue) {
        Write-ColorOutput "Using NSSM to install Windows Service..." $Green
        $currentDir = Get-Location
        nssm install "BrevoAPI" "uvicorn" "$ApiService --host 0.0.0.0 --port $ApiPort"
        nssm set "BrevoAPI" AppDirectory "$currentDir"
        nssm install "BrevoBackground" "python" "-m $BackgroundService"
        nssm set "BrevoBackground" AppDirectory "$currentDir"
        Write-ColorOutput "Services installed. Use sc start BrevoAPI and sc start BrevoBackground to start them" $Green
    } else {
        Write-ColorOutput "Creating scheduled tasks instead..." $Yellow
        # Create scheduled tasks as fallback
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File `"$PWD\run_service.ps1`" start"
        $trigger = New-ScheduledTaskTrigger -AtStartup
        Register-ScheduledTask -TaskName "BrevoService" -Action $action -Trigger $trigger -Description "Brevo Background Service"
        Write-ColorOutput "Scheduled task created. Service will start at system boot" $Green
    }
}

function Uninstall-Service {
    Write-ColorOutput "Uninstalling Brevo Service..." $Yellow
    
    if (Get-Command nssm -ErrorAction SilentlyContinue) {
        nssm stop "BrevoAPI"
        nssm stop "BrevoBackground"
        nssm remove "BrevoAPI" confirm
        nssm remove "BrevoBackground" confirm
    }
    
    Unregister-ScheduledTask -TaskName "BrevoService" -Confirm:$false -ErrorAction SilentlyContinue
    Write-ColorOutput "Service uninstalled" $Green
}

function Show-Help {
    Write-ColorOutput "Brevo Service Management (PowerShell)" $Blue
    Write-Host "Usage: .\run_service.ps1 [start|stop|restart|status|logs|install|uninstall]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  start     - Start both API and background services (stops existing if running)"
    Write-Host "  stop      - Stop all services"
    Write-Host "  restart   - Stop and start services"
    Write-Host "  status    - Check service status and process count"
    Write-Host "  logs      - View live logs"
    Write-Host "  install   - Install as Windows service (requires admin)"
    Write-Host "  uninstall - Remove Windows service (requires admin)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run_service.ps1 start    # Start services"
    Write-Host "  .\run_service.ps1 restart  # Cleanly restart services"
    Write-Host "  .\run_service.ps1 status   # Check if running"
    Write-Host "  .\run_service.ps1 logs     # Monitor logs"
    Write-Host "  .\run_service.ps1 stop     # Stop services"
    Write-Host ""
    Write-ColorOutput "Pro tip: Run as Administrator for Windows Service installation" $Yellow
}

# Main execution
switch ($Action) {
    "start" { Start-Services }
    "stop" { Stop-Services }
    "restart" { Restart-Services }
    "status" { Show-Status }
    "logs" { Show-Logs }
    "install" { Install-Service }
    "uninstall" { Uninstall-Service }
    default { Show-Help }
} 