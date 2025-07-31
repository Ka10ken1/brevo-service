# Brevo Background Service

##
- Most important part rewrite in GO or Rust

A cross-platform background service for managing Brevo email contacts and campaigns. Features a modern web-based log viewer and supports both Linux/macOS and Windows.

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

## 🔧 API Endpoints

- `POST /add_contact` - Add single contact to Brevo
- `POST /send-info` - Send info email to contact
- `POST /process-csv` - Bulk process CSV files
- `GET /docs` - Interactive API documentation


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
