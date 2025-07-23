# Brevo Service Runner for Windows (PowerShell)
# Usage: .\run_service.ps1 [start|stop|restart|status|logs|install|uninstall]

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "install", "uninstall", "help")]
    [string]$Action = "help"
)

$ServiceNameApi = "api_service"
$ServiceNameBg = "background_service"

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
    if (-not $ProcessId) { return $false }
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        return $process -ne $null
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
            # Invalid PID file or not running
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
    return $null
}

function Test-ServiceRunning($ServiceName) {
    $pid = Get-ServicePID $ServiceName
    return $pid -ne $null
}

# Recursive function to kill a process and all its children
function Kill-ProcessTree($pid) {
    if (-not (Test-ProcessRunning $pid)) { return }
    try {
        # Find child processes
        $children = Get-WmiObject Win32_Process -Filter "ParentProcessId = $pid" -ErrorAction SilentlyContinue
        foreach ($child in $children) {
            Kill-ProcessTree $child.ProcessId
        }
        Write-ColorOutput "Killing process PID $pid and its children..." $Yellow
        Stop-Process -Id $pid -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
        # Force kill if still running
        if (Test-ProcessRunning $pid) {
            Write-ColorOutput "Force killing PID $pid..." $Red
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        }
    }
    catch {
        Write-ColorOutput "Failed to kill PID $pid: $($_.Exception.Message)" $Red
    }
}

function Stop-Service($ServiceName) {
    $pidFile = "$ServiceName.pid"
    
    Write-ColorOutput "Stopping $ServiceName..." $Yellow
    
    # Stop by PID file (recursive)
    if (Test-Path $pidFile) {
        try {
            $processId = [int](Get-Content $pidFile -Raw).Trim()
            if (Test-ProcessRunning $processId) {
                Write-ColorOutput "Stopping $ServiceName (PID: $processId)..." $Yellow
                Kill-ProcessTree $processId
            }
        }
        catch {
            Write-ColorOutput "Error reading PID file: $($_.Exception.Message)" $Yellow
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
    
    # Also kill any lingering processes by port or command line pattern
    if ($ServiceName -eq $ServiceNameApi) {
        Write-ColorOutput "Checking for lingering API processes..." $Yellow

        # Kill processes using port
        try {
            $connections = netstat -ano | Select-String ":$ApiPort "
            foreach ($connection in $connections) {
                if ($connection -match '\s+(\d+)$') {
                    $pid = $matches[1]
                    if (Test-ProcessRunning $pid) {
                        Write-ColorOutput "Killing process using port $ApiPort (PID: $pid)" $Yellow
                        Kill-ProcessTree $pid
                    }
                }
            }
        }
        catch {
            Write-ColorOutput "Could not check port usage: $($_.Exception.Message)" $Yellow
        }

        # Kill python uvicorn processes running brevo.main
        try {
            Get-Process -Name "python" -ErrorAction SilentlyContinue | ForEach-Object {
                try {
                    $procId = $_.Id
                    $processArgs = (Get-WmiObject Win32_Process -Filter "ProcessId = $procId" -ErrorAction SilentlyContinue).CommandLine
                    if ($processArgs -and $processArgs -like "*uvicorn*" -and $processArgs -like "*brevo.main*") {
                        Write-ColorOutput "Killing uvicorn python process (PID: $procId)" $Yellow
                        Kill-ProcessTree $procId
                    }
                }
                catch {}
            }
        }
        catch {
            Write-ColorOutput "Could not enumerate uvicorn processes" $Yellow
        }
    }
    elseif ($ServiceName -eq $ServiceNameBg) {
        Write-ColorOutput "Checking for lingering background processes..." $Yellow

        # Kill python background service processes
        try {
            Get-Process -Name "python" -ErrorAction SilentlyContinue | ForEach-Object {
                try {
                    $procId = $_.Id
                    $processArgs = (Get-WmiObject Win32_Process -Filter "ProcessId = $procId" -ErrorAction SilentlyContinue).CommandLine
                    if ($processArgs -and $processArgs -like "*brevo.background_service*") {
                        Write-ColorOutput "Killing background service process (PID: $procId)" $Yellow
                        Kill-ProcessTree $procId
                    }
                }
                catch {}
            }
        }
        catch {
            Write-ColorOutput "Could not enumerate background processes" $Yellow
        }
    }

    Start-Sleep -Seconds 2

    if (Test-ServiceRunning $ServiceName) {
        Write-ColorOutput "WARNING: $ServiceName may still be running" $Yellow
    }
    else {
        Write-ColorOutput "$ServiceName stopped successfully" $Green
    }
}

function Stop-AllBrevoProcesses {
    Write-ColorOutput "Stopping ALL Brevo-related processes..." $Red

    try {
        # Kill by port first
        $connections = netstat -ano | Select-String ":$ApiPort "
        foreach ($connection in $connections) {
            if ($connection -match '\s+(\d+)$') {
                $pid = $matches[1]
                Write-ColorOutput "Killing process on port $ApiPort (PID: $pid)" $Yellow
                Kill-ProcessTree $pid
            }
        }

        # Kill all Brevo-related python processes
        Get-Process -Name "python" -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $procId = $_.Id
                $processArgs = (Get-WmiObject Win32_Process -Filter "ProcessId = $procId" -ErrorAction SilentlyContinue).CommandLine
                if ($processArgs -and ($processArgs -like "*brevo*" -or $processArgs -like "*uvicorn*")) {
                    Write-ColorOutput "Killing Python process (PID: $procId): $processArgs" $Yellow
                    Kill-ProcessTree $procId
                }
            }
            catch {}
        }

        # Clean up PID files
        Remove-Item "*.pid" -Force -ErrorAction SilentlyContinue

        Write-ColorOutput "All Brevo processes stopped" $Green
    }
    catch {
        Write-ColorOutput "Error during cleanup: $($_.Exception.Message)" $Red
    }
}

function Start-Services {
    Write-ColorOutput "Starting Brevo Services..." $Blue
    
    if (Test-ServiceRunning $ServiceNameApi) {
        Write-ColorOutput "WARNING: API service is already running. Stopping it first..." $Yellow
        Stop-Service $ServiceNameApi
    }
    
    if (Test-ServiceRunning $ServiceNameBg) {
        Write-ColorOutput "WARNING: Background service is already running. Stopping it first..." $Yellow
        Stop-Service $ServiceNameBg
    }
    
    if (-not (Test-Path ".env")) {
        Write-ColorOutput "Warning: .env file not found. Please create one with BREVO_API_KEY" $Yellow
    }
    
    if (-not $env:VIRTUAL_ENV) {
        Write-ColorOutput "Tip: Consider activating your virtual environment first" $Yellow
    }
    
    Write-ColorOutput "Starting API service on port $ApiPort..." $Green
    $apiProcess = Start-Process -FilePath "uvicorn" -ArgumentList "$ApiService", "--host", "0.0.0.0", "--port", "$ApiPort", "--reload" -RedirectStandardOutput "api_service.log" -RedirectStandardError "api_service_error.log" -WindowStyle Hidden -PassThru
    $apiProcess.Id | Out-File -FilePath "api_service.pid" -Encoding UTF8

    Start-Sleep -Seconds 2

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

    Stop-Service $ServiceNameApi
    Stop-Service $ServiceNameBg

    # Nuclear option if anything still alive
    if ((Test-ServiceRunning $ServiceNameApi) -or (Test-ServiceRunning $ServiceNameBg)) {
        Write-ColorOutput "Some services still running, using force cleanup..." $Yellow
        Stop-AllBrevoProcesses
    }

    Write-ColorOutput "All services stopped" $Green
}

function Show-Status {
    Write-ColorOutput "Brevo Service Status:" $Blue

    if (Test-ServiceRunning $ServiceNameApi) {
        $apiPid = Get-ServicePID $ServiceNameApi
        Write-ColorOutput "   API Service: Running (PID: $apiPid)" $Green
    }
    else {
        Write-ColorOutput "   API Service: Not running" $Red
    }

    if (Test-ServiceRunning $ServiceNameBg) {
        $bgPid = Get-ServicePID $ServiceNameBg
        Write-ColorOutput "   Background Service: Running (PID: $bgPid)" $Green
    }
    else {
        Write-ColorOutput "   Background Service: Not running" $Red
    }

    Write-Output ""
    Write-ColorOutput "Process Analysis:" $Blue

    $brevoProcs = @(Get-Process | Where-Object {
        ($_.ProcessName -eq "python" -and ($_.CommandLine -like "*uvicorn*brevo*" -or $_.CommandLine -like "*brevo.background_service*")) -or
        ($_.ProcessName -eq "uvicorn" -and $_.CommandLine -like "*brevo*")
    })

    if ($brevoProcs.Count -gt 0) {
        Write-ColorOutput "   Total Brevo-related processes: $($brevoProcs.Count)" $Blue
        if ($brevoProcs.Count -gt 2) {
            Write-ColorOutput "   WARNING: Multiple processes detected. Consider running stop first." $Yellow
        }
    }
    else {
        Write-ColorOutput "   No Brevo processes found" $Blue
    }

    Write-ColorOutput "   Log viewer: http://localhost:$ApiPort" $Blue

    $memUsage = [math]::Round((Get-Process python -ErrorAction SilentlyContinue | Measure-Object WorkingSet -Sum).Sum / 1MB, 2)
    if ($memUsage -gt 0) {
        Write-ColorOutput "   Python Memory Usage: ${memUsage}MB" $Blue
    }
}

function Restart-Services {
    Write-ColorOutput "Restarting Brevo Services..." $Blue

    Stop-Service $ServiceNameApi
    Stop-Service $ServiceNameBg

    Start-Sleep -Seconds 2

    if (-not (Test-Path ".env")) {
        Write-ColorOutput "Warning: .env file not found. Please create one with BREVO_API_KEY" $Yellow
    }

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

    if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
        Write-ColorOutput "❌ This operation requires administrator privileges" $Red
        Write-ColorOutput "Please run PowerShell as Administrator and try again" $Yellow
        return
    }

    if (Get-Command nssm -ErrorAction SilentlyContinue) {
        Write-ColorOutput "Using NSSM to install Windows Service..." $Green
        $currentDir = Get-Location
        nssm install "BrevoAPI" "uvicorn" "$ApiService --host 0.0.0.0 --port $ApiPort"
        nssm set "BrevoAPI" AppDirectory "$currentDir"
        nssm install "BrevoBackground" "python" "-m $BackgroundService"
        nssm set "BrevoBackground" AppDirectory "$currentDir"
        Write-ColorOutput "Services installed. Use sc start BrevoAPI and sc start BrevoBackground to start them" $Green
    }
    else {
        Write-ColorOutput "Creating scheduled tasks instead..." $Yellow
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
    Write-Host "  start     - Start both API and background services (stops existing ones first)"
    Write-Host "  stop      - Stop both API and background services gracefully"
    Write-Host "  restart   - Restart services"
    Write-Host "  status    - Show current status of services"
    Write-Host "  logs      - Tail service logs"
    Write-Host "  install   - Install as Windows service (requires admin & NSSM)"
    Write-Host "  uninstall - Remove installed Windows service"
    Write-Host "  help      - Show this help message"
}

switch ($Action) {
    "start"   { Start-Services }
    "stop"    { Stop-Services }
    "restart" { Restart-Services }
    "status"  { Show-Status }
    "logs"    { Show-Logs }
    "install" { Install-Service }
    "uninstall" { Uninstall-Service }
    default   { Show-Help }
}

