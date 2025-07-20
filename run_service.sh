#!/bin/bash

# Brevo Service Runner
# Usage: ./run_service.sh [start|stop|status|logs]

SERVICE_NAME="brevo-service"
API_PORT=8010
BACKGROUND_SERVICE="brevo.background_service"
API_SERVICE="brevo.main:app"

# Function to check if a service is running
is_service_running() {
    local service_name=$1
    local pid_file="${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # Service is running
        else
            rm -f "$pid_file"  # Clean up stale PID file
            return 1  # Service not running
        fi
    fi
    return 1  # PID file doesn't exist
}

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "🛑 Stopping $service_name (PID: $pid)..."
            kill "$pid"
            sleep 2
            if ps -p "$pid" > /dev/null 2>&1; then
                echo "⚡ Force killing $service_name..."
                kill -9 "$pid"
            fi
        fi
        rm -f "$pid_file"
    fi
    
    # Also kill any lingering processes by name
    if [ "$service_name" = "api_service" ]; then
        pkill -f "uvicorn brevo.main:app" 2>/dev/null || true
    elif [ "$service_name" = "background_service" ]; then
        pkill -f "python -m brevo.background_service" 2>/dev/null || true
    fi
}

case "$1" in
    start)
        echo "🚀 Starting Brevo Services..."
        
        if is_service_running "api_service"; then
            echo "⚠️  API service is already running. Stopping it first..."
            stop_service "api_service"
        fi
        
        if is_service_running "background_service"; then
            echo "⚠️  Background service is already running. Stopping it first..."
            stop_service "background_service"
        fi
        
        if [ ! -f ".env" ]; then
            echo "⚠️  Warning: .env file not found. Please create one with BREVO_API_KEY"
        fi
        
        echo "📡 Starting API service on port $API_PORT..."
        nohup uvicorn $API_SERVICE --host 0.0.0.0 --port $API_PORT --reload > api_service.log 2>&1 &
        API_PID=$!
        echo $API_PID > api_service.pid
        
        echo "⚙️  Starting background service..."
        nohup python -m $BACKGROUND_SERVICE > background_service.log 2>&1 &
        BG_PID=$!
        echo $BG_PID > background_service.pid
        
        echo "✅ Services started successfully!"
        echo "   📊 Log viewer: http://localhost:$API_PORT"
        echo "   📝 API docs: http://localhost:$API_PORT/docs"
        echo "   📋 API PID: $API_PID"
        echo "   🔧 Background PID: $BG_PID"
        ;;
        
    stop)
        echo "🛑 Stopping Brevo Services..."
        
        stop_service "api_service"
        stop_service "background_service"
        
        echo "✅ All services stopped"
        ;;
        
    status)
        echo "📊 Brevo Service Status:"
        
        # Check API service
        if is_service_running "api_service"; then
            API_PID=$(cat api_service.pid)
            echo "   📡 API Service: ✅ Running (PID: $API_PID)"
        else
            echo "   📡 API Service: ❌ Not running"
        fi
        
        if is_service_running "background_service"; then
            BG_PID=$(cat background_service.pid)
            echo "   🔧 Background Service: ✅ Running (PID: $BG_PID)"
        else
            echo "   🔧 Background Service: ❌ Not running"
        fi
        
        echo ""
        echo "🔍 Process Analysis:"
        brevo_processes=$(ps aux | grep -E "(uvicorn brevo|python.*brevo)" | grep -v grep | wc -l)
        if [ "$brevo_processes" -gt 0 ]; then
            echo "   Total Brevo-related processes: $brevo_processes"
            if [ "$brevo_processes" -gt 2 ]; then
                echo "   ⚠️  Warning: Multiple processes detected. Consider running 'stop' first."
            fi
        else
            echo "   No Brevo processes found"
        fi
        
        echo "   🌐 Log viewer: http://localhost:$API_PORT"
        ;;
        
    restart)
        echo "🔄 Restarting Brevo Services..."
        stop_service "api_service"
        stop_service "background_service"
        sleep 2
        
        # Check if .env exists
        if [ ! -f ".env" ]; then
            echo "⚠️  Warning: .env file not found. Please create one with BREVO_API_KEY"
        fi
        
        # Start services
        echo "📡 Starting API service on port $API_PORT..."
        nohup uvicorn $API_SERVICE --host 0.0.0.0 --port $API_PORT --reload > api_service.log 2>&1 &
        API_PID=$!
        echo $API_PID > api_service.pid
        
        echo "⚙️  Starting background service..."
        nohup python -m $BACKGROUND_SERVICE > background_service.log 2>&1 &
        BG_PID=$!
        echo $BG_PID > background_service.pid
        
        echo "✅ Services restarted successfully!"
        echo "   📊 Log viewer: http://localhost:$API_PORT"
        echo "   📝 API docs: http://localhost:$API_PORT/docs"
        echo "   📋 API PID: $API_PID"
        echo "   🔧 Background PID: $BG_PID"
        ;;
        
    logs)
        echo "📋 Viewing service logs (Ctrl+C to exit)..."
        tail -f api_service.log background_service.log brevo_service.log 2>/dev/null || echo "No log files found yet"
        ;;
        
    *)
        echo "🚀 Brevo Service Management"
        echo "Usage: $0 [start|stop|restart|status|logs]"
        echo ""
        echo "Commands:"
        echo "  start   - Start both API and background services (stops existing if running)"
        echo "  stop    - Stop all services"
        echo "  restart - Stop and start services"
        echo "  status  - Check service status and process count"
        echo "  logs    - View live logs"
        echo ""
        echo "Example:"
        echo "  $0 start    # Start services"
        echo "  $0 restart  # Cleanly restart services"
        echo "  $0 status   # Check if running"
        echo "  $0 logs     # Monitor logs"
        echo "  $0 stop     # Stop services"
        exit 1
        ;;
esac 