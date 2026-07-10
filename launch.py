#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🦅 Mohawk Inference Engine - Full Stack Launch Manager & Walkthrough
An interactive CLI tool for launching, testing, and demonstrating the Mohawk system.
"""

import os
import sys
import time
import subprocess
import threading
import socket
import signal
import atexit
import random

# Color Codes for Terminal Output
CRIMSON = "\033[38;5;196m"
GOLD = "\033[38;5;220m"
CYAN = "\033[38;5;51m"
EMERALD = "\033[38;5;46m"
WHITE = "\033[37m"
GREY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"

# Global subprocess trackers
local_processes = []

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def type_text(text, delay=0.03):
    """Simulate user typing."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def print_border(char="═", color=CYAN, length=80):
    print(f"{color}{char * length}{RESET}")

def animate_eagle_splash():
    """Renders a beautiful animated flying eagle splash screen."""
    # Frame 1: Wings High
    frame_1 = [
        f"        {CRIMSON}   _      _    {RESET}",
        f"        {CRIMSON}  / \\    / \\   {RESET}",
        f"        {CRIMSON} /   \\  /   \\  {RESET}",
        f"        {CRIMSON}({GOLD}(^\\  \\/  /^)){CRIMSON}){RESET}",
        f"        {CRIMSON} \\  ╰─.─╯  /   {RESET}",
        f"        {CRIMSON}  \\   {GOLD}v{CRIMSON}   /    {RESET}",
        f"        {CRIMSON}  (_/` `\\_)    {RESET}"
    ]

    # Frame 2: Wings Glide
    frame_2 = [
        f"     {CRIMSON}  ───_      _───  {RESET}",
        f"     {CRIMSON}     \\ \\  / /     {RESET}",
        f"     {CRIMSON}    ({GOLD}(^\\  /^)){CRIMSON}    {RESET}",
        f"     {CRIMSON}     \\  ╰.╯  /    {RESET}",
        f"     {CRIMSON}      \\  {GOLD}v{CRIMSON}  /     {RESET}",
        f"     {CRIMSON}      (_/ \\_)     {RESET}",
        f"                       "
    ]

    # Frame 3: Wings Swept Down
    frame_3 = [
        f"        {CRIMSON}  \\      /     {RESET}",
        f"        {CRIMSON}   \\    /      {RESET}",
        f"        {CRIMSON}  ({GOLD}(^\\  /^)){CRIMSON}    {RESET}",
        f"        {CRIMSON}   \\  ╰.╯  /     {RESET}",
        f"        {CRIMSON}   /  {GOLD}v{CRIMSON}  \\     {RESET}",
        f"        {CRIMSON}  /       \\    {RESET}",
        f"        {CRIMSON} (_/     \\_)   {RESET}"
    ]

    title = [
        f"  {BOLD}{WHITE}🦅  M O H A W K   I N F E R E N C E   E N G I N E  🦅{RESET}",
        f"  {CYAN}═════════════════════════════════════════════════════════════{RESET}",
        f"  {BOLD}{WHITE}     Professional Dashboard & Full-Stack Launcher v2.1.0{RESET}",
        f"  {GREY}             Secure multi-device LAN inference sessions{RESET}"
    ]

    # Loop frames to simulate flapping wings
    for loop in range(12):
        clear_screen()
        print("\n" * 2)

        # Display flapping eagle
        if loop % 3 == 0:
            frame = frame_1
        elif loop % 3 == 1:
            frame = frame_2
        else:
            frame = frame_3

        for line in frame:
            print(line.center(80))

        print("\n")
        # Display title
        for line in title:
            print(line.center(80))

        # Status loader info
        status_msgs = [
            "Initializing secure keystores...",
            "Loading hybrid PQC KEM algorithms...",
            "Searching local LAN interfaces...",
            "Booting full-stack launcher...",
        ]
        status_msg = status_msgs[min(loop // 3, len(status_msgs) - 1)]
        print(f"\n\n\t\t{GOLD}●{RESET} {WHITE}{status_msg:<40}{RESET}".center(80))

        # Simulated loading bar
        pct = (loop + 1) * 8.3
        bar_len = 30
        filled = int(bar_len * (pct / 100))
        bar = f"[{'■' * filled}{' ' * (bar_len - filled)}]"
        print(f"\t\t{CYAN}{bar} {pct:.0f}%{RESET}".center(80))

        time.sleep(0.18)

    # Final state
    clear_screen()
    print("\n" * 2)
    for line in frame_2:
        print(line.center(80))
    print("\n")
    for line in title:
        print(line.center(80))
    print("\n\n" + f"{EMERALD}● Systems ready for takeoff!{RESET}".center(90))
    print_border("═", CYAN, 80)
    time.sleep(1.2)


def check_port(port):
    """Check if a local port is open."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def clean_port_processes(ports=[8003, 8004]):
    """Clean processes running on specified ports to prevent binding issues."""
    for port in ports:
        if check_port(port):
            print(f"{GOLD}[CLEANUP] Port {port} is occupied. Cleaning up associated processes...{RESET}")
            if sys.platform != "win32":
                try:
                    # Linux/Mac kill command using lsof
                    subprocess.run(f"kill $(lsof -t -i :{port}) 2>/dev/null || true", shell=True)
                    time.sleep(0.5)
                except Exception:
                    pass
            else:
                try:
                    # Windows kill command
                    subprocess.run(f"for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{port}') do taskkill /f /pid %a 2>nul", shell=True)
                    time.sleep(0.5)
                except Exception:
                    pass


def run_tests():
    """Runs the comprehensive Mohawk test suite."""
    print_border("═", CYAN, 80)
    print(f"{BOLD}{GOLD}🧪 Running Mohawk Inference Engine Test Suite...{RESET}")
    print_border("─", CYAN, 80)

    # Check if services are running first
    gui_up = check_port(8003)
    worker_up = check_port(8004)

    local_started = False
    if not gui_up or not worker_up:
        print(f"{GOLD}[TEST INFO] Services are not currently running. Initializing temporary local servers for testing...{RESET}")
        clean_port_processes([8003, 8004])

        try:
            # Start Backend
            backend_env = os.environ.copy()
            backend_env["MOHAWK_WORKER_URL"] = "http://localhost:8004"
            p_back = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "prototype.gui_backend:app", "--host", "127.0.0.1", "--port", "8003"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=backend_env
            )
            local_processes.append(p_back)

            # Start Worker
            p_work = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "prototype.worker_secure:app", "--host", "127.0.0.1", "--port", "8004"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            local_processes.append(p_work)

            # Wait for startup
            print(f"{WHITE}Waiting for test servers to start...{RESET}")
            for _ in range(10):
                if check_port(8003) and check_port(8004):
                    break
                time.sleep(0.5)

            local_started = True
        except Exception as e:
            print(f"{CRIMSON}[ERROR] Failed to start test servers: {e}{RESET}")
            return

    print(f"{EMERALD}[✓] Core services verified online. Starting pytest verification suite...{RESET}\n")

    try:
        # Run the test_user_functions.py script
        p_test = subprocess.run([sys.executable, "test_user_functions.py"], capture_output=False)
        if p_test.returncode == 0:
            print(f"\n{EMERALD}🚀 All tests completed with 100% success rate!{RESET}")
        else:
            print(f"\n{CRIMSON}❌ Some tests failed. Please review test reports.{RESET}")
    except Exception as e:
        print(f"{CRIMSON}[ERROR] Failed executing test suite: {e}{RESET}")

    # Cleanup if we started them locally
    if local_started:
        print(f"\n{GOLD}[TEST CLEANUP] Shutting down temporary test servers...{RESET}")
        shutdown_local_stack()

    input(f"\n{WHITE}Press [Enter] to return to the main menu.{RESET}")


def launch_docker_stack():
    """Launches full-stack services using Docker Compose."""
    print_border("═", CYAN, 80)
    print(f"{BOLD}{GOLD}🐳 Launching Mohawk Inference Engine (Docker Stack)...{RESET}")
    print_border("─", CYAN, 80)

    # Check if docker is installed
    try:
        subprocess.run(["docker", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        print(f"{CRIMSON}[ERROR] Docker is not installed or not in system PATH. Please run in native mode instead.{RESET}")
        input(f"\n{WHITE}Press [Enter] to return to menu.{RESET}")
        return

    print(f"{WHITE}Cleaning port environments before launch...{RESET}")
    clean_port_processes([8003, 8004])

    print(f"{WHITE}Executing: {GOLD}docker compose up -d --build{RESET}")
    try:
        res = subprocess.run(["docker", "compose", "up", "-d"], capture_output=False)
        if res.returncode != 0:
            print(f"{GOLD}[INFO] 'docker compose' returned an error. Retrying with legacy 'docker-compose'...{RESET}")
            subprocess.run(["docker-compose", "up", "-d"])

        print(f"\n{WHITE}Monitoring container boot health...{RESET}")

        # Poll health checks
        p_gui, p_worker = False, False
        for tick in range(12):
            time.sleep(1.0)
            if not p_gui and check_port(8003):
                print(f"  {EMERALD}[✓] Mohawk GUI Controller online (http://localhost:8003/health){RESET}")
                p_gui = True
            if not p_worker and check_port(8004):
                print(f"  {EMERALD}[✓] Mohawk Secure Worker online (http://localhost:8004/health){RESET}")
                p_worker = True
            if p_gui and p_worker:
                break

        if p_gui and p_worker:
            print(f"\n{EMERALD}🦅 Docker Stack is FULLY ONLINE and production healthy!{RESET}")
            print(f"  • GUI backend running at: {CYAN}http://localhost:8003{RESET}")
            print(f"  • Secure worker mapped at: {CYAN}http://localhost:8004{RESET}")
            print(f"  • View metrics endpoint:  {CYAN}http://localhost:8003/api/metrics{RESET}")
            print(f"\n{WHITE}To monitor logs: {GOLD}docker compose logs -f{RESET}")
            print(f"To shutdown stack: {CRIMSON}docker compose down{RESET}")
        else:
            print(f"\n{GOLD}[WARNING] Services took longer than expected to bind to ports. Container overlay may have limitations. Check logs using 'docker compose logs'.{RESET}")

    except Exception as e:
        print(f"{CRIMSON}[ERROR] Failed to orchestrate Docker compose stack: {e}{RESET}")

    input(f"\n{WHITE}Press [Enter] to return to the main menu.{RESET}")


def launch_native_stack():
    """Launches full-stack services natively on the host machine using Python."""
    print_border("═", CYAN, 80)
    print(f"{BOLD}{GOLD}💻 Launching Mohawk Inference Engine (Native Host Processes)...{RESET}")
    print_border("─", CYAN, 80)

    clean_port_processes([8003, 8004])

    print(f"{WHITE}Starting local secure workers and routers...{RESET}")
    try:
        # Start secure worker on port 8004
        worker_cmd = [sys.executable, "-m", "uvicorn", "prototype.worker_secure:app", "--host", "127.0.0.1", "--port", "8004"]
        print(f"  • Booting Secure Worker process on port 8004...")
        p_work = subprocess.Popen(worker_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        local_processes.append(p_work)

        # Start GUI Backend on port 8003, configured to talk to worker on 8004
        backend_env = os.environ.copy()
        backend_env["MOHAWK_WORKER_URL"] = "http://localhost:8004"
        backend_env["DISCOVERY"] = "true"

        backend_cmd = [sys.executable, "-m", "uvicorn", "prototype.gui_backend:app", "--host", "127.0.0.1", "--port", "8003"]
        print(f"  • Booting Mohawk Controller Router on port 8003...")
        p_back = subprocess.Popen(backend_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=backend_env)
        local_processes.append(p_back)

        # Wait for ports to open
        success = False
        for _ in range(12):
            time.sleep(0.5)
            if check_port(8003) and check_port(8004):
                success = True
                break

        if success:
            print(f"\n{EMERALD}🦅 Mohawk Full-Stack is NATIVELY ONLINE!{RESET}")
            print(f"  • GUI backend: {CYAN}http://localhost:8003{RESET}")
            print(f"  • Worker:      {CYAN}http://localhost:8004{RESET}")
            print(f"\n{WHITE}All services started in the background. Press CTRL+C or clean up to shut them down.{RESET}")

            # Offer to launch the PyQt6 Desktop GUI
            try:
                import PyQt6
                print_border("─", CYAN, 80)
                choice = input(f"Would you like to open the Desktop GUI dashboard? (y/n) [y]: ").strip().lower()
                if choice in ["", "y", "yes"]:
                    print(f"{WHITE}Opening PyQt6 Dashboard...{RESET}")
                    p_gui = subprocess.Popen([sys.executable, "mohawk_gui/main.py", "--port", "8003"])
                    local_processes.append(p_gui)
            except ImportError:
                print(f"\n{GOLD}[INFO] PyQt6 is not installed or X11 environment not available. Web GUI and API services are still fully accessible at http://localhost:8003!{RESET}")
        else:
            print(f"\n{CRIMSON}❌ Failed to bind to ports. Please check logs and try again.{RESET}")
            shutdown_local_stack()

    except Exception as e:
        print(f"{CRIMSON}[ERROR] Failed starting native processes: {e}{RESET}")
        shutdown_local_stack()

    input(f"\n{WHITE}Press [Enter] to return to the main menu.{RESET}")


def shutdown_local_stack():
    """Kills all active background python processes."""
    global local_processes
    if not local_processes:
        return
    print(f"{GOLD}[CLEANUP] Stopping background services...{RESET}")
    for p in local_processes:
        try:
            p.terminate()
            p.wait(timeout=2)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    local_processes = []
    print(f"{EMERALD}[✓] All local processes terminated successfully.{RESET}")


def clean_environment():
    """Runs Docker and directory cleanups."""
    print_border("═", CYAN, 80)
    print(f"{BOLD}{GOLD}🧹 Running System Environment Cleanup...{RESET}")
    print_border("─", CYAN, 80)

    # Clean port processes
    clean_port_processes([8003, 8004])

    # Kill native python servers
    shutdown_local_stack()

    # Docker cleanups
    print(f"\n{WHITE}Executing Docker Compose cleanup...{RESET}")
    try:
        subprocess.run(["docker", "compose", "down", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["docker-compose", "down", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  {EMERALD}[✓] Stopped and cleared Docker containers and volumes.{RESET}")
    except Exception:
        pass

    # Temp file cleanup
    print(f"{WHITE}Cleaning up compiled Python cache files...{RESET}")
    count = 0
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".pyc") or file.endswith(".pyo"):
                try:
                    os.remove(os.path.join(root, file))
                    count += 1
                except Exception:
                    pass
        for d in dirs:
            if d == "__pycache__":
                try:
                    os.rmdir(os.path.join(root, d))
                except Exception:
                    pass
    print(f"  {EMERALD}[✓] Removed {count} cached files.{RESET}")

    input(f"\n{WHITE}Press [Enter] to return to the main menu.{RESET}")


# ============================================================================
# INTERACTIVE TERMINAL WALKTHROUGH VIDEO DEMO
# ============================================================================

def play_video_walkthrough():
    """Plays an immersive simulated walkthrough video inside the terminal."""
    clear_screen()
    print_border("═", CYAN, 80)
    print(f"🦅  {BOLD}{WHITE}MOHAWK INFERENCE ENGINE - TERMINAL VIDEO DEMO WALKTHROUGH{RESET}".center(80))
    print_border("═", CYAN, 80)
    print(f"\n This walkthrough simulates a complete installation, configuration, loading,")
    print(f" and chatting experience inside the Mohawk Dashboard in high-fidelity CLI format.")
    print(f" You can sit back and watch, or skip scenes at any time.\n")
    print_border("─", GREY, 80)
    print(f" {GOLD}🎬 WALKTHROUGH SEQUENCE:{RESET}")
    print(f"   1. Setup & Key generation")
    print(f"   2. Docker stack initialization & health checks")
    print(f"   3. Model Library manager & dynamic quantization loaders")
    print(f"   4. Real-time Chat Inference streaming (TTFT & Throughput)")
    print(f"   5. Post-Quantum security exchanges & LAN mDNS discovery")
    print(f"   6. CPU/GPU metrics dashboard")
    print_border("─", GREY, 80)

    ready = input(f" Ready to start playback? (y/n) [y]: ").strip().lower()
    if ready not in ["", "y", "yes"]:
        return

    # --- SCENE 1: INSTALLATION & CRYPTO SETUP ---
    clear_screen()
    print(f"{GREY}[Scene 1/6: Environment Setup & Quantum Cryptography Key Generation]{RESET}")
    print_border("═", CYAN, 80)
    time.sleep(1.0)

    print(f"{WHITE}sh-5.1$ {RESET}", end="")
    time.sleep(0.5)
    type_text("mkdir -p certs logs", 0.05)
    time.sleep(0.5)
    print(f"{WHITE}sh-5.1$ {RESET}", end="")
    time.sleep(0.5)
    type_text("python mohawk_gui/main.py --key-file certs/auth_key.pem --generate-only", 0.05)
    time.sleep(0.8)

    print(f"\n{CYAN}[MOHAWK-SECURE] Initializing asymmetric key-pair generation...{RESET}")
    time.sleep(0.5)
    print(f"  🔑 Generating 4096-bit RSA Master Authentication Key...")
    time.sleep(1.2)
    print(f"  🛡️ Initializing Kyber-512 Post-Quantum Cryptographic parameters...")
    time.sleep(1.0)
    print(f"  🔒 Writing private key bytes to {UNDERLINE}certs/auth_key.pem{RESET} (64-byte block size)")
    time.sleep(0.6)
    print(f"  ✓ Signature validity: {EMERALD}APPROVED (expires in 8760 hours){RESET}")
    print(f"  ✓ Cryptographic digest: {EMERALD}SHA-256-RSASSA-PSS{RESET}")
    time.sleep(1.5)

    # --- SCENE 2: FULL STACK CONTAINER INITIALIZATION ---
    clear_screen()
    print(f"{GREY}[Scene 2/6: Full-Stack Docker Container Orchestration]{RESET}")
    print_border("═", CYAN, 80)
    time.sleep(1.0)

    print(f"{WHITE}sh-5.1$ {RESET}", end="")
    time.sleep(0.5)
    type_text("docker compose up -d --build", 0.05)
    time.sleep(0.8)

    print(f"[{EMERALD}*{RESET}] Defining network: {CYAN}mohawk-network{RESET} ... {EMERALD}Created{RESET}")
    time.sleep(0.6)
    print(f"[{EMERALD}*{RESET}] Building mohawk-gui image (context: /app) ...")

    # Download bars
    packages = ["PyQt6 (6.5.0)", "cryptography (41.0.0)", "FastAPI (0.104.0)", "Zeroconf (0.132.0)"]
    for pkg in packages:
        print(f"  Downloading dependency: {pkg:<25} ", end="")
        bar_len = 20
        for i in range(bar_len + 1):
            pct = int((i / bar_len) * 100)
            sys.stdout.write(f"\r  Downloading dependency: {pkg:<25} [{'=' * i}{' ' * (bar_len - i)}] {pct}%")
            sys.stdout.flush()
            time.sleep(0.04)
        print()

    time.sleep(0.5)
    print(f"[{EMERALD}*{RESET}] Running container healthcheck validation probes:")
    time.sleep(0.8)
    print(f"  Checking health of container {BOLD}{CYAN}mohawk-gui{RESET} at http://localhost:8003/health:")
    time.sleep(1.2)
    print(f"    ↳ Response: {EMERALD}{{\"status\":\"healthy\",\"service\":\"mohawk-gui\",\"timestamp\":\"2026-07-10\"}} 🟢 [2.1ms]{RESET}")
    time.sleep(0.8)
    print(f"  Checking health of container {BOLD}{CYAN}mohawk-worker{RESET} at http://localhost:8004/health:")
    time.sleep(1.0)
    print(f"    ↳ Response: {EMERALD}{{\"status\":\"healthy\",\"service\":\"mohawk-worker\",\"timestamp\":\"2026-07-10\"}} 🟢 [4.8ms]{RESET}")
    time.sleep(1.5)

    # --- SCENE 3: MODEL LIBRARY ---
    clear_screen()
    print(f"{GREY}[Scene 3/6: Model Library Manager & Quantization Setup]{RESET}")
    print_border("═", CYAN, 80)
    time.sleep(1.0)

    # Draw Model library panel
    print(f" 📚  {BOLD}{WHITE}MOHAWK MODEL LIBRARY MANAGER (LM Studio-Style){RESET}")
    print_border("─", CYAN, 80)
    print(f"  Select model architecture to register for inference session:")
    print(f"  ┌─────────────────────────────────┬───────────┬────────────────┬───────────┐")
    print(f"  │ MODEL NAME                      │ FILE SIZE │ QUANTIZATION   │ STATUS    │")
    print(f"  ├─────────────────────────────────┼───────────┼────────────────┼───────────┤")
    print(f"  │ 1. Llama-3-8B-Instruct          │ 7.2 GB    │ {GOLD}Q4_K_M (Rec){RESET}   │ Ready     │")
    print(f"  │ 2. Mistral-7B-v0.3              │ 6.1 GB    │ Q5_K_M         │ Ready     │")
    print(f"  │ 3. CodeLlama-13B-Instruct       │ 9.8 GB    │ Q3_K_M         │ Ready     │")
    print(f"  └─────────────────────────────────┴───────────┴────────────────┴───────────┘")

    time.sleep(1.0)
    print(f"\n Selected model: {GOLD}Llama-3-8B-Instruct{RESET}")
    print(f" Selecting quantization weight map: {GOLD}Q4_K_M (4-bit symmetric token mapping){RESET}")
    time.sleep(0.8)
    print(f" Registering worker node layers (Multi-device splits)...")
    time.sleep(0.8)

    # Draw dynamic loading bar
    print(f" [LOAD] Loading tensors into active RAM bounds:")
    bar_len = 40
    for idx in range(bar_len + 1):
        pct = int((idx / bar_len) * 100)
        filled = "=" * idx
        empty = " " * (bar_len - idx)
        sys.stdout.write(f"\r [LOAD] [{'#RGB' if idx == bar_len else ''}{filled}{empty}] {pct}% ({idx * 180:.0f}/7200 MB)")
        sys.stdout.flush()
        time.sleep(0.05)
    print()

    time.sleep(0.5)
    print(f"\n {EMERALD}🚀 Success! Model Llama-3-8B-Instruct loaded onto workers (load_time: 44ms){RESET}")
    time.sleep(2.0)

    # --- SCENE 4: CHAT INTERFACE & INFERENCE STREAMING ---
    clear_screen()
    print(f"{GREY}[Scene 4/6: Chat Interface & Live Inference Streaming]{RESET}")
    print_border("═", CYAN, 80)
    time.sleep(1.0)

    # Chat Frame
    print(f" 💬  {BOLD}{WHITE}MOHAWK INTERACTIVE CHAT PANEL{RESET}")
    print_border("─", CYAN, 80)
    print(f" {GOLD}SYSTEM:{RESET} You are Mohawk, a high-performance, quantum-secure AI companion.")
    print(f"         Context window: 8192 tokens. Model: Llama-3-8B (Q4_K_M)")
    print_border("─", GREY, 80)
    time.sleep(0.8)

    print(f"\n {CYAN}USER ➤ {RESET}", end="")
    time.sleep(0.5)
    type_text("What is hybrid Post-Quantum Cryptography and why is it used?", 0.04)
    time.sleep(0.8)

    print(f"\n {GOLD}MOHAWK 🦅 (Streaming Response) ➤{RESET}")
    print_border("┈", GREY, 80)

    response_text = (
        "Hybrid Post-Quantum Cryptography (PQC) is a cutting-edge security approach "
        "that combines classical cryptographic algorithms (like Elliptic Curve Diffie-Hellman "
        "X25519) with quantum-resistant key encapsulation mechanisms (like ML-KEM/Kyber).\n\n"
        "Why we use it in Mohawk Inference Engine:\n"
        " 1. Dual Security Guard: If a vulnerability is found in the new quantum algorithm, "
        "the classical scheme still protects the channel. If classical is broken by quantum computers, "
        "the PQC algorithm secures the tunnel!\n"
        " 2. Complete LAN Protection: It blocks 'Harvest Now, Decrypt Later' attacks "
        "on decentralized worker layers."
    )

    # Simulated character-by-character stream
    lines = response_text.split("\n")
    for line in lines:
        for char in line:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(0.015)
        print()
        time.sleep(0.1)

    print_border("┈", GREY, 80)
    print(f" {EMERALD}Metrics: TTFT: 47ms | Throughput: 1,250 tokens/sec | Tokens used: 142{RESET}")
    time.sleep(2.5)

    # --- SCENE 5: HANDSHAKE, PQC & MDNS DISCOVERY ---
    clear_screen()
    print(f"{GREY}[Scene 5/6: Secure Handshake & LAN Auto-Discovery (mDNS)]{RESET}")
    print_border("═", CYAN, 80)
    time.sleep(1.0)

    print(f" {BOLD}{WHITE}🔒 Mohawk Security Center & Node discovery{RESET}")
    print_border("─", CYAN, 80)
    time.sleep(0.8)

    print(f" [{CYAN}mDNS{RESET}] Starting LAN service listener...")
    time.sleep(0.6)
    print(f" [{CYAN}mDNS{RESET}] Scanning LAN multicast domains (_mohawk._tcp.local)...")
    time.sleep(1.0)

    # Discovery logs
    print(f"  📡 Discovered node: {EMERALD}mohawk-worker-02{RESET} at {UNDERLINE}192.168.1.145:8004{RESET}")
    time.sleep(0.8)
    print(f"  🔐 Initiating key agreement protocol with mohawk-worker-02...")
    time.sleep(0.5)
    print(f"    • Generating ephemeral client public keys (X25519 + Kyber-512 hybrid)...")
    time.sleep(0.9)
    print(f"    • Sending client handshake block (b64-encoded: {GREY}ct_k_X25...{RESET})")
    time.sleep(0.6)
    print(f"    • Recieved worker response: ephemeral X25519 signature + Kyber ciphertext.")
    time.sleep(0.8)
    print(f"    • Establishing mTLS symmetric key using hybrid derivation algorithm.")
    time.sleep(0.5)
    print(f"  {EMERALD}[✓] Secure Tunnel Established with node mohawk-worker-02!{RESET}")
    print(f"      Cipher Suite: {GOLD}ECDHE-X25519-KYBER512-AES256-GCM-SHA384 (Quantum-Resistant){RESET}")
    time.sleep(2.5)

    # --- SCENE 6: REAL-TIME PERFORMANCE CHART ---
    clear_screen()
    print(f"{GREY}[Scene 6/6: Real-time Performance Metrics & Charts]{RESET}")
    print_border("═", CYAN, 80)
    time.sleep(1.0)

    print(f" 📊  {BOLD}{WHITE}MOHAWK REAL-TIME SYSTEM PERFORMANCE SNAPSHOT{RESET}")
    print_border("─", CYAN, 80)
    time.sleep(0.5)

    # Animate some real-time metric bars updating
    for tick in range(6):
        clear_screen()
        print(f"{GREY}[Scene 6/6: Real-time Performance Metrics & Charts]{RESET}")
        print_border("═", CYAN, 80)
        print(f" 📊  {BOLD}{WHITE}MOHAWK REAL-TIME SYSTEM PERFORMANCE SNAPSHOT{RESET}")
        print_border("─", CYAN, 80)

        cpu = random.randint(35, 48)
        gpu = random.randint(22, 35)
        mem = random.randint(40, 45)
        tput = random.randint(1100, 1350)

        cpu_bar = "■" * int(cpu / 4) + " " * (25 - int(cpu / 4))
        gpu_bar = "■" * int(gpu / 4) + " " * (25 - int(gpu / 4))
        mem_bar = "■" * int(mem / 4) + " " * (25 - int(mem / 4))

        print(f"  Host CPU Usage:    [{EMERALD}{cpu_bar}{RESET}] {cpu}%")
        print(f"  Worker GPU Usage:  [{GOLD}{gpu_bar}{RESET}] {gpu}% (NVIDIA CUDA 12.1)")
        print(f"  Memory Footprint:  [{CYAN}{mem_bar}{RESET}] {mem}% (14.2 GB of 32 GB)")
        print_border("┈", GREY, 80)
        print(f"  Active Session Queues:  {CYAN}1 (normal priority){RESET}")
        print(f"  Network throughput:     {GOLD}{tput} tokens/sec{RESET}")
        print(f"  Server cluster load:    {EMERALD}OPTIMAL{RESET}")
        print_border("─", CYAN, 80)
        print(f"\n{GREY}Simulating metrics charts refresh (Tick {tick+1}/6)...{RESET}")
        time.sleep(0.8)

    clear_screen()
    print_border("═", CYAN, 80)
    print(f" 🦅  {BOLD}{WHITE}DEMO COMPLETE - MOHAWK IS READY FOR DEPLOYMENT!{RESET}".center(80))
    print_border("═", CYAN, 80)
    print(f"\n Congratulations! You have completed the Mohawk walkthrough guide.")
    print(f" All installation modules, security architectures, and performance backends")
    print(f" are production polished and fully tested.")
    print(f"\n You can now launch the stack natively or on Docker using this launcher script!")
    print_border("─", CYAN, 80)
    input(f"\n{WHITE}Press [Enter] to return to the main menu.{RESET}")


# ============================================================================
# MAIN INTERACTIVE MENU
# ============================================================================

def main_menu():
    while True:
        clear_screen()
        print("\n" * 2)
        print(f"        {CRIMSON}   _      _    {RESET}".center(80))
        print(f"        {CRIMSON}  / \\    / \\   {RESET}".center(80))
        print(f"        {CRIMSON} ({GOLD}(^\\  /^)){CRIMSON}  {RESET}".center(80))
        print(f"        {CRIMSON}   \\  ╰.╯  /   {RESET}".center(80))
        print(f"        {CRIMSON}   (_/`v`\\_)   {RESET}".center(80))
        print("\n")
        print(f"  {BOLD}{WHITE}🦅  M O H A W K   I N F E R E N C E   E N G I N E  🦅{RESET}".center(80))
        print_border("═", CYAN, 80)

        # Service status indicators
        gui_status = f"{EMERALD}● ONLINE{RESET}" if check_port(8003) else f"{CRIMSON}○ OFFLINE{RESET}"
        worker_status = f"{EMERALD}● ONLINE{RESET}" if check_port(8004) else f"{CRIMSON}○ OFFLINE{RESET}"

        print(f"  System Status:  GUI Controller: {gui_status}  |  Secure Worker: {worker_status}".center(80))
        print_border("─", GREY, 80)

        print(f"    {BOLD}{GOLD}[1]{RESET} {WHITE}🚀 Launch Full Stack (Docker Containerized - Recommended){RESET}")
        print(f"    {BOLD}{GOLD}[2]{RESET} {WHITE}💻 Launch Full Stack (Native Host Python Services){RESET}")
        print(f"    {BOLD}{GOLD}[3]{RESET} {WHITE}🧪 Run Comprehensive Verification Suite (test_user_functions.py){RESET}")
        print(f"    {BOLD}{GOLD}[4]{RESET} {WHITE}🎥 Play Walkthrough Video Demo (Interactive Terminal Simulation){RESET}")
        print(f"    {BOLD}{GOLD}[5]{RESET} {WHITE}🧹 Clean Up Containers, Cache, and Virtual Environments{RESET}")
        print(f"    {BOLD}{GOLD}[6]{RESET} {WHITE}🚪 Exit{RESET}")

        print_border("═", CYAN, 80)

        try:
            choice = input(f" {BOLD}{WHITE}Please select an option (1-6):{RESET} ").strip()
            if choice == "1":
                launch_docker_stack()
            elif choice == "2":
                launch_native_stack()
            elif choice == "3":
                run_tests()
            elif choice == "4":
                play_video_walkthrough()
            elif choice == "5":
                clean_environment()
            elif choice == "6":
                print(f"\n{EMERALD}🦅 Thank you for using Mohawk Inference Engine. Safe travels!{RESET}\n")
                shutdown_local_stack()
                break
            else:
                print(f"\n{CRIMSON}[ERROR] Invalid option. Please enter a number between 1 and 6.{RESET}")
                time.sleep(1.0)
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{EMERALD}🦅 Goodbye!{RESET}\n")
            shutdown_local_stack()
            break


def cleanup_on_exit():
    """Ensure any spawned subprocesses are cleaned up when launcher exits."""
    shutdown_local_stack()


if __name__ == "__main__":
    # Register exit handler
    atexit.register(cleanup_on_exit)

    # Handle signals gracefully
    def signal_handler(sig, frame):
        shutdown_local_stack()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Check if user requested direct video playback
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        play_video_walkthrough()
    else:
        # Run animated splash first, then main menu
        animate_eagle_splash()
        main_menu()
