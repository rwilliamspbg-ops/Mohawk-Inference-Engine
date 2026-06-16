#!/bin/bash
# =============================================================================
# Mohawk Inference Engine GUI - Linux Build Script
# Version: 2.1.0 - Production Ready
# =============================================================================

echo "═══════════════════════════════════════════════════════════"
echo "  MOHAWK INFERENCE ENGINE GUI - Linux Build System v2.1.0"
echo "═══════════════════════════════════════════════════════════"
echo

# Check Python version
python3 --version
echo

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo

# Build executable with PyInstaller
echo "Building standalone executable..."
pyinstaller \
    --name=Mohawk-Inference-Engine \
    --onefile \
    --windowed \
    --add-data="mohawk_gui/resources:resources" \
    --hidden-import=mohawk_gui.main \
    --hidden-import=mohawk_gui.auth_manager \
    --hidden-import=mohawk_gui.connection_pool \
    --hidden-import=mohawk_gui.metrics_buffer \
    --hidden-import=mohawk_gui.error_recovery \
    --hidden-import=mohawk_gui.monitoring \
    --hidden-import=mohawk_gui.audit_logger \
    mohawk_gui/main.py

echo
echo "═══════════════════════════════════════════════════════════"
echo "  BUILD COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo
echo "Executable location: dist/Mohawk*-Inference-Engine"
echo

# Show dist directory contents
ls -la dist/*.spec 2>/dev/null || echo "No .spec files found"
ls -la dist/ 2>/dev/null | grep -v ".spec" || echo "Executable not found"

echo
echo "═══════════════════════════════════════════════════════════"
echo "  NEXT STEPS:"
echo "═══════════════════════════════════════════════════════════"
echo
echo "1. Copy the executable to your deployment location"
echo "   Example: cp dist/Mohawk*-Inference-Engine /usr/local/bin/"
echo
echo "2. Make it executable (if not already)"
echo "   chmod +x /usr/local/bin/Mohawk-Inference-Engine"
echo
echo "3. Run the executable (first run will generate auth key)"
echo "   ./Mohawk-Inference-Engine --host localhost --port 8003"
echo
echo "4. For production, configure SSL certificates in certs/ directory"
echo
echo "5. Use docker-compose.yml for containerized deployment"
echo
echo "═══════════════════════════════════════════════════════════"
echo
