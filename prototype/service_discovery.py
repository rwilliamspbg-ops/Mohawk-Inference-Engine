#!/usr/bin/env python3
"""Mohawk Service Discovery - LAN auto-discovery for Mohawk nodes.

Provides automatic discovery of Mohawk services on the LAN using mDNS/Zeroconf.
Allows clients to find and connect to GUI and worker nodes without manual IP entry.
"""

import asyncio
import ipaddress
import logging
import socket
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

try:
    from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf
except ImportError:
    Zeroconf = None
    ServiceStateChange = None

logger = logging.getLogger(__name__)

@dataclass
class MohawkService:
    """Represents a discovered Mohawk service on the LAN."""

    name: str  # Service name (e.g., "Mohawk-GUI-001")
    service_type: str  # "gui" or "worker"
    host: str  # Hostname or IP address
    port: int  # Port number
    addresses: List[str]  # List of IP addresses
    properties: Dict[str, str]  # Additional metadata
    discovered_at: str  # ISO timestamp
    ttl: int = 4500  # Time to live (seconds)

    @property
    def url(self) -> str:
        """Return the service URL."""
        if self.addresses:
            ip = self.addresses[0]
            return f"http://{ip}:{self.port}"
        return f"http://{self.host}:{self.port}"

    @property
    def is_ipv4(self) -> bool:
        """Check if service has IPv4 address."""
        return any(self._is_ipv4(addr) for addr in self.addresses)

    @staticmethod
    def _is_ipv4(addr: str) -> bool:
        try:
            ipaddress.IPv4Address(addr)
            return True
        except (ipaddress.AddressValueError, ValueError):
            return False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

class MohawkServiceDiscovery:
    """Handles mDNS service discovery for Mohawk nodes on LAN."""

    # mDNS service types
    MOHAWK_GUI_TYPE = "_mohawk-gui._tcp.local."
    MOHAWK_WORKER_TYPE = "_mohawk-worker._tcp.local."

    def __init__(
        self,
        on_service_added: Optional[Callable] = None,
        on_service_removed: Optional[Callable] = None,
    ):
        """
        Initialize service discovery.

        Args:
            on_service_added: Callback when service is discovered
            on_service_removed: Callback when service is lost
        """
        self.on_service_added = on_service_added
        self.on_service_removed = on_service_removed

        self.zeroconf: Optional[Zeroconf] = None
        self.browsers: Dict[str, ServiceBrowser] = {}
        self.discovered_services: Dict[str, MohawkService] = {}
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> bool:
        """Start service discovery. Returns True if mDNS is available."""
        if not Zeroconf:
            logger.warning("Zeroconf not available; LAN discovery disabled")
            return False

        try:
            self.zeroconf = Zeroconf(interfaces=["127.0.0.1"])
            self._running = True

            # Browse for GUI services
            self.browsers[self.MOHAWK_GUI_TYPE] = ServiceBrowser(
                self.zeroconf,
                self.MOHAWK_GUI_TYPE,
                handlers=[self._on_service_state_change],
            )

            # Browse for Worker services
            self.browsers[self.MOHAWK_WORKER_TYPE] = ServiceBrowser(
                self.zeroconf,
                self.MOHAWK_WORKER_TYPE,
                handlers=[self._on_service_state_change],
            )

            logger.info(
                "Service discovery started - listening for Mohawk services on LAN"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start service discovery: {e}")
            self._running = False
            return False

    def stop(self):
        """Stop service discovery."""
        if self.zeroconf:
            self.zeroconf.close()
        self._running = False
        logger.info("Service discovery stopped")

    def _on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ):
        """Handle service state changes (discovery/removal)."""
        if state_change == ServiceStateChange.Added:
            self._add_service(zeroconf, service_type, name)
        elif state_change == ServiceStateChange.Removed:
            self._remove_service(name)

    def _add_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Add discovered service."""
        try:
            info = zeroconf.get_service_info(service_type, name)
            if not info:
                return

            # Parse service info
            svc_type = "gui" if "gui" in service_type.lower() else "worker"
            addresses = [
                addr.decode() if isinstance(addr, bytes) else addr
                for addr in (info.parsed_addresses() or [])
            ]

            properties = {}
            if info.properties:
                properties = {
                    k.decode() if isinstance(k, bytes) else k: (
                        v.decode() if isinstance(v, bytes) else v
                    )
                    for k, v in info.properties.items()
                }

            service = MohawkService(
                name=name,
                service_type=svc_type,
                host=info.server or "unknown",
                port=info.port,
                addresses=addresses or ["127.0.0.1"],
                properties=properties,
                discovered_at=datetime.now().isoformat(),
            )

            with self._lock:
                self.discovered_services[name] = service

            logger.info(f"Service discovered: {service.url} ({svc_type})")

            if self.on_service_added:
                self.on_service_added(service)

        except Exception as e:
            logger.error(f"Error adding service {name}: {e}")

    def _remove_service(self, name: str):
        """Remove service when it goes offline."""
        with self._lock:
            if name in self.discovered_services:
                service = self.discovered_services.pop(name)
                logger.info(f"Service removed: {service.name}")

                if self.on_service_removed:
                    self.on_service_removed(service)

    def get_services(self, service_type: Optional[str] = None) -> List[MohawkService]:
        """Get all discovered services, optionally filtered by type."""
        with self._lock:
            services = list(self.discovered_services.values())

        if service_type:
            services = [s for s in services if s.service_type == service_type]

        return services

    def find_gui_services(self) -> List[MohawkService]:
        """Find all discovered GUI services."""
        return self.get_services("gui")

    def find_worker_services(self) -> List[MohawkService]:
        """Find all discovered worker services."""
        return self.get_services("worker")

    def get_service_by_name(self, name: str) -> Optional[MohawkService]:
        """Get service by name."""
        with self._lock:
            return self.discovered_services.get(name)

class LanServiceRegistry:
    """Register and manage Mohawk services for LAN discovery."""

    def __init__(
        self,
        hostname: str,
        service_type: str,
        port: int,
        properties: Optional[Dict[str, str]] = None,
    ):
        """
        Register a Mohawk service for discovery.

        Args:
            hostname: Service hostname (e.g., "mohawk-gui-001")
            service_type: "gui" or "worker"
            port: Service port
            properties: Metadata (version, model, etc.)
        """
        self.hostname = hostname
        self.service_type = service_type
        self.port = port
        self.properties = properties or {}
        self.zeroconf: Optional[Zeroconf] = None

    def register(self) -> bool:
        """Register service on mDNS. Returns True if successful."""
        if not Zeroconf:
            logger.warning("Zeroconf not available; service registration disabled")
            return False

        try:
            from zeroconf import ServiceInfo

            service_name = f"{self.hostname}._mohawk-{self.service_type}._tcp.local."
            service_type = f"_mohawk-{self.service_type}._tcp.local."

            # Get local IP
            hostname_parts = socket.gethostname()
            local_ip = socket.gethostbyname(socket.gethostname())

            info = ServiceInfo(
                service_type,
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties=self.properties,
                server=f"{hostname_parts}.local.",
            )

            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(info)

            logger.info(f"Service registered: {service_name} at {local_ip}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to register service: {e}")
            return False

    def unregister(self):
        """Unregister service."""
        if self.zeroconf:
            self.zeroconf.close()
            logger.info("Service unregistered")

def get_local_ip() -> str:
    """Get local IP address."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"

async def discover_services_async(timeout: float = 5.0) -> List[MohawkService]:
    """Discover services asynchronously with timeout."""
    discovery = MohawkServiceDiscovery()

    if not discovery.start():
        return []

    try:
        await asyncio.sleep(timeout)
        services = discovery.get_services()
        return services
    finally:
        discovery.stop()

if __name__ == "__main__":
    # Demo: start discovery and list services
    import time

    logging.basicConfig(level=logging.INFO)

    def on_added(service):
        print(f"✓ Found: {service.name} at {service.url}")

    def on_removed(service):
        print(f"✗ Lost: {service.name}")

    discovery = MohawkServiceDiscovery(
        on_service_added=on_added, on_service_removed=on_removed
    )

    print("Starting LAN service discovery (10 seconds)...")
    discovery.start()

    time.sleep(10)

    print("\nDiscovered services:")
    for svc in discovery.get_services():
        print(f"  - {svc.name:30} ({svc.service_type:6}) -> {svc.url}")

    discovery.stop()
