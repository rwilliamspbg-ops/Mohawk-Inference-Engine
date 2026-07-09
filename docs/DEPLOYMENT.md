# Deployment Guide for Mohawk Inference Engine

This guide covers production deployment patterns, containerization, and orchestration.

## Table of Contents

- [Docker Compose Setup](#docker-compose-setup)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Multi-Node Cluster Configuration](#multi-node-cluster-configuration)
- [Monitoring Stack Integration](#monitoring-stack-integration)
- [Security Hardening](#security-hardening)
- [Performance Tuning](#performance-tuning)

---

## Docker Compose Setup

### Single Worker Node

```yaml
version: '3.8'
services:
  mohawk-worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    ports:
      - "8003:8003"
    volumes:
      - model_weights:/app/weights:ro
      - /dev/nvidia0:/dev/nvidia0  # GPU passthrough if available
    environment:
      - WORKER_PORT=8003
      - OQS_INSTALL_PATH=/usr/local
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/metrics"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  model_weights:
```

### Two-Worker Cluster with Controller

```yaml
version: '3.8'
services:
  controller:
    build:
      context: .
      dockerfile: Dockerfile.controller
    ports:
      - "9000:9000"
    environment:
      - WORKERS=controller-worker1:8003,controller-worker2:8003
      - OQS_INSTALL_PATH=/usr/local
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
      interval: 30s

  controller-worker1:
    build:
      context: .
      dockerfile: Dockerfile.worker
    ports:
      - "8001:8003"
    volumes:
      - model_weights:/app/weights:ro
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  controller-worker2:
    build:
      context: .
      dockerfile: Dockerfile.worker
    ports:
      - "8002:8003"
    volumes:
      - model_weights:/app/weights:ro
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  model_weights:
```

---

## Kubernetes Deployment

### Worker StatefulSet (Multi-Replica)

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mohawk-worker
  labels:
    app: mohawk-worker
    version: v0.2.0
spec:
  serviceName: mohawk-worker
  replicas: 3
  selector:
    matchLabels:
      app: mohawk-worker
  template:
    metadata:
      labels:
        app: mohawk-worker
        version: v0.2.0
    spec:
      containers:
      - name: worker
        image: rwilliamspbg-ops/mohawk-worker:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8003
          name: inference
        resources:
          requests:
            memory: "16Gi"
            cpu: "4"
          limits:
            memory: "24Gi"
            cpu: "8"
        env:
        - name: WORKER_PORT
          value: "8003"
        - name: OQS_INSTALL_PATH
          value: "/usr/local"
        - name: ENABLE_PQC
          value: "true"
        volumeMounts:
        - name: model-weights
          mountPath: /app/weights
          readOnly: true
        livenessProbe:
          httpGet:
            path: /metrics
            port: 8003
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /metrics
            port: 8003
          initialDelaySeconds: 30
          periodSeconds: 15
      volumes:
      - name: model-weights
        persistentVolumeClaim:
          claimName: model-weights-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-weights-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  storageClassName: gp3
```

### Controller Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mohawk-controller
  labels:
    app: mohawk-controller
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mohawk-controller
  template:
    metadata:
      labels:
        app: mohawk-controller
    spec:
      containers:
      - name: controller
        image: rwilliamspbg-ops/mohawk-controller:latest
        ports:
        - containerPort: 9000
          name: api
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
          limits:
            memory: "16Gi"
            cpu: "4"
        env:
        - name: WORKERS
          valueFrom:
            configMapKeyRef:
              name: mohawk-workers-config
              key: worker-addresses
```

---

## Multi-Node Cluster Configuration

### Node Inventory File

Create `cluster/inventory.json`:

```json
{
  "nodes": [
    {
      "id": "node-gpu-01",
      "address": "192.168.1.10",
      "device_type": "gpu",
      "gpu_model": "NVIDIA_A100_80GB",
      "memory_total_gb": 80,
      "memory_free_gb": 45,
      "cpu_cores": 96,
      "network_interface": "eth0:10Gbps"
    },
    {
      "id": "node-cpu-01",
      "address": "192.168.1.11",
      "device_type": "cpu",
      "cpu_cores": 64,
      "network_interface": "eth0:25Gbps"
    }
  ],
  "topology": {
    "gpu_nodes": ["node-gpu-01"],
    "cpu_nodes": ["node-cpu-01"]
  }
}
```

### Cluster Registration Script

```python
#!/usr/bin/env python3
"""Register cluster nodes with controller."""

import json
import requests
import argparse

def register_cluster(controller_url, inventory_file):
    """Register cluster inventory with controller."""
    with open(inventory_file) as f:
        inventory = json.load(f)
    
    response = requests.post(
        f"{controller_url}/api/v1/cluster/register",
        json={"nodes": inventory["nodes"]}
    )
    response.raise_for_status()
    print(f"Cluster registered successfully")
    print(response.json())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--controller", required=True)
    parser.add_argument("--inventory", required=True)
    args = parser.parse_args()
    
    register_cluster(args.controller, args.inventory)
```

---

## Monitoring Stack Integration

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'mohawk_worker'
    static_configs:
      - targets: 
          - 'worker-1.mohawk-cluster.internal:8003'
          - 'worker-2.mohacht-cluster.internal:8003'
          - 'worker-3.mohawk-cluster.internal:8003'
    metrics_path: /metrics
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance

  - job_name: 'mohawk_controller'
    static_configs:
      - targets: ['controller.mohawk-cluster.internal:9000']
    
  - job_name: 'node_exporter'
    static_configs:
      - targets: 
          - 'worker-1.mohawk-cluster.internal:9100'
          - 'worker-2.mohawk-cluster.internal:9100'
          - 'worker-3.mohawk-cluster.internal:9100'
```

### Grafana Dashboard JSON

Create `grafana/mohawk-dashboard.json`:

```json
{
  "dashboard": {
    "id": null,
    "uid": "mohawk-inference",
    "title": "Mohawk Inference Engine Dashboard",
    "type": "grafana",
    "version": 1,
    "refresh": "10s",
    "rows": [
      {
        "title": "Throughput & Latency",
        "panels": [
          {
            "title": "Inferences Per Second",
            "datasource": "Prometheus",
            "targets": [
              {
                "expr": "rate(mohawk_inferences_total[1m])",
                "legendFormat": "{{instance}}"
              }
            ]
          },
          {
            "title": "P99 Latency (ms)",
            "datasource": "Prometheus",
            "targets": [
              {
                "expr": "histogram_quantile(0.99, rate(mohawk_inference_duration_ms_bucket[5m]))"
              }
            ]
          }
        ]
      },
      {
        "title": "Resource Utilization",
        "panels": [
          {
            "title": "GPU Memory Usage",
            "datasource": "Prometheus",
            "targets": [
              {
                "expr": "node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes"
              }
            ]
          },
          {
            "title": "CPU Utilization",
            "datasource": "Prometheus",
            "targets": [
              {
                "expr": "100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

---

## Security Hardening

### Environment Variables for Production

```bash
# Controller environment
export CONTROLLER_WORKERS="worker1:8003,worker2:8003,worker3:8003"
export CONTROLLER_PORT=9000
export CONTROLLER_ENABLE_PQC=true
export CONTROLLER_REPLAY_WINDOW=3600  # seconds
export CONTROLLER_CIRCUIT_BREAKER_THRESHOLD=5
export CONTROLLER_CIRCUIT_BREAKER_TIMEOUT=30

# Worker environment
export WORKER_PORT=8003
export WORKER_ENABLE_TELEMETRY=true
export WORKER_METRICS_PATH=/metrics
export OQS_INSTALL_PATH=/usr/local
export WORKER_PQC_ALGORITHM=Kyber768:X25519

# Security
export CONTROLLER_SIGNING_KEY_FILE=/etc/mohawk/signing.key
export WORKER_IDENTITY_CERT_FILE=/etc/mohawk/identity.crt
```

### TPM Attestation Configuration

```json
// attestation-config.json
{
  "attestation_mode": "required",
  "trusted_platform_module": {
    "vendor": "intel",
    "version": "2.0"
  },
  "measured_boot": true,
  "remote_attestation_endpoint": "https://attestation.mohawk-cluster.internal:443/verify"
}
```

---

## Performance Tuning

### Hugepages Configuration

Create `/etc/sysctl.conf` additions:

```bash
# Enable hugepages (2MB for EPYC-class)
echo "vm.nr_hugepages = 16384" >> /etc/sysctl.conf
sysctl -p

# For 1GB hugepages on GPU nodes
echo "vm.nr_hugepages_1048576 = 8192" >> /etc/sysctl.conf
```

### NUMA Awareness

```bash
# Bind process to specific NUMA node
numactl --cpunodebind=0 --membind=0 python prototype/worker_secure.py --port 8003

# Or in container:
cat <<EOF > numa-policy.json
{
  "mode": "interleave",
  "cpus": [0,1,2,3],
  "memory_nodes": [0]
}
EOF
```

### Kernel Parameters for High-Performance Networking

```bash
# AF_XDP optimization
echo "net.core.rmem_max = 67108864" >> /etc/sysctl.conf
echo "net.core.wmem_max = 67108864" >> /etc/sysctl.conf
echo "net.core.netdev_max_backlog = 500000" >> /etc/sysctl.conf
echo "net.ipv4.tcp_rmem = 4096 262144 67108864" >> /etc/sysctl.conf
echo "net.ipv4.tcp_wmem = 4096 262144 67108864" >> /etc/sysctl.conf
sysctl -p

# Disable TCP checksumming (if NIC supports)
echo "net.ipv4.tcp_checksum_offload = 1" >> /etc/sysctl.conf
```

---

## Scaling Patterns

### Horizontal Pod Autoscaler (Kubernetes)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mohawk-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: StatefulSet
    name: mohawk-worker
  minReplicas: 3
  maxReplicas: 12
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Load Balancer Configuration (HAProxy)

```bash
# /etc/haproxy/haproxy.cfg
frontend mohawk_api
    bind *:9000
    
    # SSL termination
    ssl crt /etc/haproxy/certs/mohawk.pem
    
    # PQC handshake support (if using ALPN)
    option alpn
  
    default_backend mohawk_workers
  
backend mohawk_workers
    balance roundrobin
    
    # Health checks
    option httpchk GET /metrics
    http-check expect status 200
    
    # Stickiness based on session ID
    cookie SESSION insert indirect nocache
    
    server worker-1 controller-worker1:8003 check cookie sess weight 100
    server worker-2 controller-worker2:8003 check cookie sess weight 100
    server worker-3 controller-worker3:8003 check cookie sess weight 100
```

---

## Disaster Recovery

### Backup Configuration

```python
# backup_strategy.py
import json
import pickle
from pathlib import Path

def backup_model_weights(model_path, backup_dir, retention_days=7):
    """Backup model weights with versioning."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"weights_backup_{timestamp}.tar.gz"
    
    # Compress weights
    import tarfile
    with tarfile.open(backup_name, "w:gz") as tar:
        tar.add(model_path, arcname="model_weights")
    
    # Rotate old backups
    cleanup_old_backups(backup_dir, retention_days)
    
    return backup_name

def restore_from_backup(backup_file, model_path):
    """Restore from compressed backup."""
    import tarfile
    with tarfile.open(backup_file, "r:gz") as tar:
        tar.extractall(path=model_path)
```

---

## Checklist for Production Deployment

- [ ] Install liboqs and configure OQS_INSTALL_PATH
- [ ] Set up TPM attestation endpoints (optional but recommended)
- [ ] Configure Prometheus/Grafana monitoring
- [ ] Set up HAProxy or Kubernetes Ingress with SSL termination
- [ ] Enable hugepages on worker nodes
- [ ] Configure circuit breakers with appropriate thresholds
- [ ] Set up backup and restore procedures for model weights
- [ ] Run fault injection tests before production launch
- [ ] Document runbooks for common failure scenarios

---

## Support & Escalation

For production issues, contact:
- **Severity 1** (Outage): #mohawk-oncall-slack
- **Severity 2** (Performance degradation): mohawk-ops@sovereign-mohawk-proto.io
- **Security**: security@mohawk-inference.internal

See [SECURITY.md](./SECURITY.md) for incident response procedures.
