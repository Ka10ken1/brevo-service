# Brevo Background Service

A cross-platform background service for managing Brevo email contacts and campaigns. Features a modern web-based log viewer and supports both Linux/macOS and Windows.

## 🌍 Cross-Platform Support

This service runs on:
- **Linux** - Using bash scripts
- **macOS** - Using bash scripts  
- **Windows** - Using PowerShell and batch scripts

## ⚡ Quick Start

### 1. Setup Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure API key
echo "BREVO_API_KEY=your_key_here" > .env
```

### 2. Run Services

**Linux/macOS:**
```bash
./run_service.sh start    # Start services
./run_service.sh status   # Check status
./run_service.sh logs     # View logs
./run_service.sh stop     # Stop services
```

**Windows (PowerShell - Recommended):**
```powershell
.\run_service.ps1 start    # Start services
.\run_service.ps1 status   # Check status
.\run_service.ps1 logs     # View logs
.\run_service.ps1 stop     # Stop services
```

**Windows (Batch):**
```cmd
run_service.bat start    # Start services
run_service.bat status   # Check status
run_service.bat logs     # View logs
run_service.bat stop     # Stop services
```

## 📊 Web Dashboard

Visit `http://localhost:8000` for:
- **Real-time log viewer** with dark terminal theme
- **Service status** monitoring
- **Error tracking** and statistics
- **Live log streaming** with color-coded levels

## 🔧 API Endpoints

- `POST /add_contact` - Add single contact to Brevo
- `POST /send-info` - Send info email to contact
- `POST /process-csv` - Bulk process CSV files
- `GET /docs` - Interactive API documentation

## 📋 Service Features

### Background Processing
- **Health checks** every 5 minutes
- **Automatic task processing** every 10 minutes
- **Log rotation** when files exceed 10MB
- **Daily status reports** at 9:00 AM

### CSV Processing
Handles your Georgian business directory CSV format:
- Extracts emails from `Email` column
- Supports Unicode (Georgian text)
- Adds contacts to Brevo lists
- Sends follow-up emails

### Cross-Platform Logging
- **Unified logging** across all platforms
- **Color-coded** log levels (INFO, WARNING, ERROR)
- **Automatic rotation** and cleanup
- **Real-time web viewer**

## 🎯 Production Deployment

### Linux/macOS (systemd)
```bash
# Create systemd service
sudo cp brevo.service /etc/systemd/system/
sudo systemctl enable brevo
sudo systemctl start brevo
```

### Windows Service
```powershell
# Install as Windows Service (requires admin)
.\run_service.ps1 install

# Start service
sc start BrevoAPI
sc start BrevoBackground
```

## 📁 Project Structure

```
brevo-service/
├── brevo/
│   ├── main.py              # FastAPI app with log viewer
│   ├── background_service.py # Cross-platform daemon
│   ├── brevo_service.py     # Core Brevo API integration
│   └── router.py            # REST API endpoints
├── static/
│   └── index.html           # Log viewer dashboard
├── run_service.sh           # Linux/macOS script
├── run_service.ps1          # Windows PowerShell script
├── run_service.bat          # Windows batch script
├── README-Windows.md        # Windows-specific instructions
├── .env                     # Environment variables
└── requirements.txt         # Python dependencies
```

## 🔒 Security

- **Environment variables** for API keys
- **Input validation** on all endpoints
- **Error handling** without exposing internals
- **Log sanitization** for sensitive data

## 🚀 Advanced Features

### Windows-Specific
- **NSSM integration** for robust Windows Services
- **Event Viewer** logging
- **PowerShell** cmdlets for management
- **Scheduled Task** fallback

### Linux/macOS-Specific  
- **systemd** service integration
- **UNIX signals** for graceful shutdown
- **Process supervision** with automatic restart

## 📖 Documentation

- **Main README** - This file (cross-platform overview)
- **README-Windows.md** - Windows-specific features and installation
- **API Documentation** - Available at `/docs` when service is running

## 🛠️ Development

```bash
# Run in development mode
uvicorn brevo.main:app --reload

# Run background service separately
python -m brevo.background_service

# View logs in real-time
tail -f *.log  # Linux/macOS
Get-Content *.log -Wait  # Windows PowerShell
```

## 📞 Support

- **Cross-platform issues** - Check this README
- **Windows-specific** - See README-Windows.md
- **API usage** - Visit `/docs` endpoint
- **Logs** - Web viewer at `http://localhost:8000`

---

**Ready to manage your Brevo contacts across any platform!** 🚀
