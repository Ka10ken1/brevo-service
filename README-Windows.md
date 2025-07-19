# Brevo Service for Windows

A cross-platform background service for managing Brevo email contacts and campaigns, with Windows-specific optimizations.

## 🚀 Quick Start for Windows

### Prerequisites

1. **Python 3.8+** installed from [python.org](https://python.org)
2. **PowerShell 5.0+** (included with Windows 10+)
3. **Brevo API Key** from your Brevo account

### Installation

1. **Clone or download the project:**
   ```powershell
   git clone <repository-url>
   cd brevo-service
   ```

2. **Create virtual environment:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```powershell
   # Create .env file with your API key
   echo "BREVO_API_KEY=your_actual_brevo_api_key_here" > .env
   ```

## 🖥️ Windows-Specific Features

### PowerShell Script (Recommended)
```powershell
# Start services
.\run_service.ps1 start

# Check status
.\run_service.ps1 status

# View logs in real-time
.\run_service.ps1 logs

# Stop services
.\run_service.ps1 stop

# Install as Windows Service (requires admin)
.\run_service.ps1 install

# Uninstall Windows Service
.\run_service.ps1 uninstall
```


## 🔧 Windows Service Installation

For production use, install as a Windows Service:

1. **Run PowerShell as Administrator**
2. **Navigate to project directory**
3. **Install service:**
   ```powershell
   .\run_service.ps1 install
   ```

This will:
- Create Windows Services for both API and background components
- Auto-start services on system boot
- Provide Windows Service management integration

### Optional: NSSM Installation

For better Windows Service integration, install [NSSM](https://nssm.cc/):

1. Download NSSM from [nssm.cc](https://nssm.cc/download)
2. Extract and add to PATH
3. Run the install command again

NSSM provides:
- Better service logging
- Automatic restart on failure
- GUI service configuration

## 📊 Monitoring

### Web Dashboard
Visit `http://localhost:8000` for:
- Real-time log viewer with dark theme
- Service status monitoring
- Error tracking and statistics

### Windows Event Viewer
When installed as a Windows Service, logs are also available in:
- Event Viewer → Windows Logs → Application
- Filter by source: "BrevoAPI" and "BrevoBackground"

### Performance Monitor
Monitor service performance using Windows Performance Toolkit:
- Memory usage tracking
- CPU utilization
- Network activity

## 🎯 API Endpoints

The service provides REST API endpoints:

- `POST /add_contact` - Add single contact
- `POST /send-info` - Send info email
- `POST /process-csv` - Process CSV files
- `GET /docs` - Interactive API documentation

### Example Usage

```powershell
# Add contact
Invoke-RestMethod -Uri "http://localhost:8000/add_contact" -Method Post -Body (@{email="user@example.com"} | ConvertTo-Json) -ContentType "application/json"

# Process CSV file
$form = @{
    file = Get-Item "contacts.csv"
}
Invoke-RestMethod -Uri "http://localhost:8000/process-csv" -Method Post -Form $form
```

## 🗂️ File Structure

```
brevo-service/
├── brevo/
│   ├── main.py                 # FastAPI application
│   ├── background_service.py   # Background daemon
│   ├── brevo_service.py        # Core Brevo API logic
│   └── router.py               # API endpoints
├── static/
│   └── index.html              # Web dashboard
├── logs/                       # Windows log directory
├── pending_csv/                # Pending CSV files
├── run_service.ps1             # PowerShell script (recommended)
├── run_service.bat             # Batch script
├── run_service.sh              # Linux/Mac script
├── .env                        # Environment variables
└── requirements.txt            # Python dependencies
```

## 🔒 Security Considerations

### Windows Defender
Add exclusions for:
- Project directory
- Python executable
- Log files

### Firewall
The service uses port 8000. Ensure Windows Firewall allows:
- Inbound connections on port 8000
- Python.exe through firewall

### User Permissions
For Windows Service installation:
- Run PowerShell as Administrator
- Ensure user has "Log on as a service" privilege

## 🚨 Troubleshooting

### Common Issues

1. **PowerShell Execution Policy:**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. **Port Already in Use:**
   ```powershell
   netstat -ano | findstr :8000
   ```

3. **Python Not Found:**
   - Verify Python is in PATH
   - Use full path in scripts if needed

4. **Service Won't Start:**
   - Check Windows Event Viewer
   - Verify .env file exists
   - Ensure dependencies are installed

### Log Locations

- **Development:** `api_service.log`, `background_service.log`
- **Windows Service:** Windows Event Viewer
- **Rotated Logs:** `logs/` directory

## 🔄 Updating

To update the service:

1. Stop services: `.\run_service.ps1 stop`
2. Update code
3. Install new dependencies: `pip install -r requirements.txt`
4. Start services: `.\run_service.ps1 start`

For Windows Services:
1. Uninstall: `.\run_service.ps1 uninstall`
2. Update code
3. Reinstall: `.\run_service.ps1 install`

## 📞 Support

For Windows-specific issues:
- Check Windows Event Viewer
- Review PowerShell execution policy
- Ensure Python and pip are properly installed
- Verify firewall and antivirus settings 