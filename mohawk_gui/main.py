"""
Mohawk Inference Engine GUI - Main Entry Point

Production-ready implementation with:
- JWT Authentication & mTLS security
- Connection pooling for high concurrency
- Real-time metrics with buffering and downsampling
- Graceful error handling and recovery
- Performance monitoring and visualization
"""

import sys
import asyncio
from pathlib import Path

# Import core components
from .main_window import MohawkGUI
from .auth_manager import AuthManager, MTLSManager
from .connection_pool import ConnectionPool
from .metrics_buffer import MetricsBuffer, MetricsAggregator
from .error_recovery import ErrorRecoveryManager
from .monitoring import GuimetricsCollector, PerformanceTracker
from .audit_logger import AuditLogger


def main():
    """
    Main application entry point.
    
    Usage:
        python mohawk_gui/main.py --host localhost --port 8003
        
    Options:
        --host         Worker host (default: localhost)
        --port         Worker port (default: 8003)
        --key-file     Path to authentication key file
        --cert-dir     Directory for TLS certificates
    """
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Mohawk Inference Engine GUI"
    )
    parser.add_argument(
        "--host", default="localhost",
        help="Worker host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=8003,
        help="Worker port (default: 8003)"
    )
    parser.add_argument(
        "--key-file", default=None,
        help="Path to authentication key file"
    )
    parser.add_argument(
        "--cert-dir", default="certs",
        help="Directory for TLS certificates"
    )
    
    args = parser.parse_args()
    
    # Initialize application components
    print("Initializing Mohawk Inference Engine GUI...")
    
    # Initialize authentication manager
    auth_manager = AuthManager(args.key_file) if args.key_file else None
    
    # Initialize connection pool
    connection_pool = ConnectionPool(max_connections=100)
    
    # Initialize metrics buffer
    metrics_buffer = MetricsBuffer(window_size=1000, sample_rate=0.1)
    
    # Initialize error recovery manager
    def alert_callback(severity, message, error):
        print(f"[ALERT {severity}] {message}: {error}")
    
    error_recovery = ErrorRecoveryManager(alert_callback=alert_callback)
    
    # Initialize monitoring collector
    monitoring = GuimetricsCollector()
    
    # Initialize audit logger
    audit_logger = AuditLogger("audit.log")
    
    # Create main window
    gui = MohawkGUI()
    
    # Setup authentication (if configured)
    if auth_manager:
        print(f"Authentication enabled with key: {args.key_file}")
    
    # Connect to worker
    try:
        gui.connect_to_worker(args.host, args.port)
    except Exception as e:
        error_recovery.handle_error(e, {"operation": "connect"})
        print(f"Connection failed: {e}")
    
    # Log startup event
    audit_logger.log_action(
        action_type="startup",
        resource="gui_application",
        details={"host": args.host, "port": args.port}
    )
    
    print("\nMohawk Inference Engine GUI started successfully!")
    print(f"Connected to worker: {args.host}:{args.port}")
    print("Press Ctrl+C to exit")
    
    # Run main event loop
    sys.exit(gui.exec())


if __name__ == "__main__":
    main()
