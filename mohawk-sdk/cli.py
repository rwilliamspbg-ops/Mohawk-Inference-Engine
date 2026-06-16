"""
CLI interface for Mohawk Inference Engine SDK.

Provides command-line tools for:
- Model benchmarking
- Session monitoring
- Configuration management
- Health checks
"""

import argparse
import json
import sys
from pathlib import Path
from mohawk_sdk import MohawkClient, create_tensor, benchmark_inference


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Mohawk Inference Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mohawk health                    # Check worker health
  mohawk benchmark model.onnx      # Benchmark inference performance
  mohawk config init               # Initialize default configuration
  mohawk monitor SESSION_ID        # Monitor active session
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Health check command
    health_parser = subparsers.add_parser(
        "health",
        help="Check worker health"
    )
    health_parser.add_argument(
        "--host",
        default="localhost",
        help="Worker host (default: localhost)"
    )
    health_parser.add_argument(
        "--port",
        type=int,
        default=8003,
        help="Worker port (default: 8003)"
    )
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Benchmark inference performance"
    )
    benchmark_parser.add_argument(
        "model_path",
        help="Path to model file (ONNX or TorchScript)"
    )
    benchmark_parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of inference iterations (default: 100)"
    )
    benchmark_parser.add_argument(
        "--warmup",
        type=int,
        default=10,
        help="Warmup iterations (default: 10)"
    )
    benchmark_parser.add_argument(
        "--host",
        default="localhost",
        help="Worker host (default: localhost)"
    )
    benchmark_parser.add_argument(
        "--port",
        type=int,
        default=8003,
        help="Worker port (default: 8003)"
    )
    
    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management"
    )
    config_subparsers = config_parser.add_subparsers(dest="subcommand")
    
    # Initialize config
    init_parser = config_subparsers.add_parser(
        "init",
        help="Initialize default configuration"
    )
    init_parser.add_argument(
        "--path",
        default=str(Path.home() / ".mohawk" / "config.toml"),
        help="Config file path (default: ~/.mohawk/config.toml)"
    )
    
    # Show config
    show_parser = config_subparsers.add_parser(
        "show",
        help="Show current configuration"
    )
    
    # Monitor command
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Monitor active session"
    )
    monitor_parser.add_argument(
        "session_id",
        help="Session ID to monitor"
    )
    monitor_parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Update interval in seconds (default: 1.0)"
    )
    
    return parser.parse_args()


def check_health(args):
    """Check worker health."""
    client = MohawkClient(
        host=args.host,
        port=args.port,
        secure=False,  # Health check doesn't require encryption
    )
    
    try:
        response = client.session.get(f"http://{args.host}:{args.port}/health")
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
            print("\n✅ Worker is healthy!")
            return 0
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return 1
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return 1


def run_benchmark(args):
    """Run inference benchmark."""
    client = MohawkClient(
        host=args.host,
        port=args.port,
        secure=True,
    )
    
    try:
        print(f"Loading model from: {args.model_path}")
        with client.load_model(args.model_path) as session:
            input_tensor = create_tensor((1, 4096))
            
            print(f"\nRunning benchmark ({args.iterations} iterations, {args.warmup} warmup)...")
            results = benchmark_inference(
                client=client,
                session=session,
                input_tensor=input_tensor,
                iterations=args.iterations,
                warmup=args.warmup
            )
            
            print("\n" + "=" * 60)
            print("Benchmark Results:")
            print("=" * 60)
            print(f"P50 Latency:     {results['p50_ms']:.2f}ms")
            print(f"P95 Latency:     {results['p95_ms']:.2f}ms")
            print(f"P99 Latency:     {results['p99_ms']:.2f}ms")
            print(f"Avg Latency:     {results['avg_ms']:.2f}ms")
            print(f"Min Latency:     {results['min_ms']:.2f}ms")
            print(f"Max Latency:     {results['max_ms']:.2f}ms")
            print(f"Throughput:      {results['throughput_tokens_per_sec']:.1f} tokens/sec")
            print("=" * 60)
            
            return 0
            
    except FileNotFoundError as e:
        print(f"\n❌ Model not found: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        return 1


def init_config(args):
    """Initialize default configuration."""
    from mohawk_sdk import MohawkConfig
    
    config = MohawkConfig(config_path=args.path)
    
    # Save default config
    config.save()
    
    print(f"\n✅ Configuration initialized at: {args.path}")
    print("\nDefault settings:")
    print("  - Worker host: localhost")
    print("  - Worker port: 8003")
    print("  - PQC enabled: true")
    print("  - Replay protection: true")
    print("  - Max concurrent sessions: 100")
    print("\nEdit the config file to customize settings.")
    
    return 0


def show_config(args):
    """Show current configuration."""
    from mohawk_sdk import MohawkConfig
    
    config = MohawkConfig()
    
    print("Current Configuration:")
    print("=" * 60)
    print(f"Worker Host: {config.get('worker.host')}")
    print(f"Worker Port: {config.get('worker.port')}")
    print(f"PQC Enabled: {config.get('security.pqc_enabled', True)}")
    print(f"Replay Protection: {config.get('security.replay_protection', True)}")
    print(f"Max Concurrent Sessions: {config.get('session.max_concurrent_sessions', 100)}")
    print("=" * 60)
    
    return 0


def monitor_session(args):
    """Monitor active session (placeholder)."""
    print(f"\nMonitoring session: {args.session_id}")
    print(f"Update interval: {args.interval}s\n")
    
    # Placeholder - would implement actual monitoring
    print("Session monitoring is not yet implemented.")
    print("Use the Python SDK for real-time monitoring:")
    print("  from mohawk_sdk import MohawkClient")
    print("  client = MohawkClient(...)")
    print("  metrics = client.get_metrics(args.session_id)")
    
    return 0


def main():
    """Main entry point."""
    args = parse_args()
    
    if not args.command:
        parser = argparse.ArgumentParser(
            description="Mohawk Inference Engine CLI",
            add_help=True
        )
        parser.print_help()
        return 1
    
    # Route to appropriate handler
    commands = {
        "health": check_health,
        "benchmark": run_benchmark,
        "config": None,  # Will be handled by subcommands
        "monitor": monitor_session,
    }
    
    if args.command == "config":
        if not args.subcommand:
            print("Error: Please specify a config subcommand")
            print("Usage: mohawk config <init|show>")
            return 1
        
        if args.subcommand == "init":
            return init_config(args)
        elif args.subcommand == "show":
            return show_config(args)
    
    if args.command in commands and commands[args.command]:
        return commands[args.command](args)
    
    print(f"Error: Unknown command '{args.command}'")
    return 1


if __name__ == "__main__":
    sys.exit(main())
