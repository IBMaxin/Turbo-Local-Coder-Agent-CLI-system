"""llama.cpp Server Manager - Handles starting/stopping llama.cpp server."""
from __future__ import annotations

import logging
import os
import subprocess
import time
import requests
from pathlib import Path
from typing import Optional

from .config import Settings


class LlamaCppServer:
    """Manages llama.cpp server process."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger("LlamaCppServer")
        self.process: Optional[subprocess.Popen] = None
        self.port = settings.llamacpp_port
        self.model_path = Path(settings.llamacpp_model_path)
        
    def is_running(self) -> bool:
        """Check if server is running and responding."""
        if self.process and self.process.poll() is None:
            # Process exists, check if responding
            try:
                resp = requests.get(f"http://127.0.0.1:{self.port}/health", timeout=2)
                return resp.status_code == 200
            except Exception:
                return False
        return False
    
    def _find_llamacpp_binary(self) -> Optional[Path]:
        """Find llama.cpp server binary."""
        # Check environment variable first
        env_binary = os.getenv("LLAMACPP_BINARY_PATH")
        if env_binary:
            binary_path = Path(env_binary)
            if binary_path.exists():
                self.logger.info(f"Using llama.cpp binary from LLAMACPP_BINARY_PATH: {binary_path}")
                return binary_path
            else:
                self.logger.warning(f"LLAMACPP_BINARY_PATH set but file not found: {binary_path}")
        
        # Check common locations
        possible_paths = [
            Path("/home/bj/llama.cpp/llama-server"),  # User's location
            Path("./llama.cpp/llama-server"),
            Path("./llama-server"),
            Path("/usr/local/bin/llama-server"),
            Path("/usr/bin/llama-server"),
            Path.home() / "llama.cpp" / "llama-server",
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_file():
                self.logger.info(f"Found llama.cpp at {path}")
                return path
        
        # Check PATH
        import shutil
        binary = shutil.which("llama-server")
        if binary:
            self.logger.info(f"Found llama-server in PATH: {binary}")
            return Path(binary)
        
        return None
    
    def _download_binary(self) -> Path:
        """Download pre-built llama.cpp binary with Vulkan support."""
        self.logger.info("Downloading llama.cpp binary with Vulkan support...")
        
        import platform
        import urllib.request
        import tarfile
        
        system = platform.system().lower()
        arch = platform.machine().lower()
        
        # Map to release names
        if system == "linux" and "x86_64" in arch:
            release_name = "llama-b4455-bin-ubuntu-x64-vulkan.zip"
        else:
            raise RuntimeError(f"No pre-built binary for {system} {arch}. Please build llama.cpp manually.")
        
        url = f"https://github.com/ggerganov/llama.cpp/releases/latest/download/{release_name}"
        
        download_dir = Path("./llama.cpp")
        download_dir.mkdir(exist_ok=True)
        
        archive_path = download_dir / release_name
        
        self.logger.info(f"Downloading from {url}...")
        urllib.request.urlretrieve(url, archive_path)
        
        # Extract
        self.logger.info("Extracting...")
        if archive_path.suffix == ".zip":
            import zipfile
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(download_dir)
        else:
            with tarfile.open(archive_path) as tar:
                tar.extractall(download_dir)
        
        binary_path = download_dir / "llama-server"
        if binary_path.exists():
            binary_path.chmod(0o755)
            self.logger.info(f"Binary installed to {binary_path}")
            return binary_path
        
        raise RuntimeError("Failed to extract llama-server binary")
    
    def _ensure_binary(self) -> Path:
        """Ensure llama.cpp binary exists, download if needed."""
        binary = self._find_llamacpp_binary()
        if binary:
            return binary
        
        self.logger.warning("llama.cpp binary not found, downloading...")
        return self._download_binary()
    
    def _ensure_model(self) -> Path:
        """Ensure model file exists."""
        if self.model_path.exists():
            self.logger.info(f"Using model: {self.model_path}")
            return self.model_path
        
        # Model not found
        raise FileNotFoundError(
            f"Model not found at {self.model_path}.\n"
            "Please set LLAMACPP_MODEL_PATH in your .env to a valid GGUF model file.\n"
            "Available models in /home/bj/llama.cpp/models:\n"
            "  - Phi-3-mini-4k-instruct-q4.gguf (recommended)\n"
            "  - SmolLM2-1.7B-Instruct-Q4_K_M.gguf\n"
            "  - functiongemma-270m-it-Q4_K_M.gguf"
        )
    
    def start(self):
        """Start llama.cpp server."""
        if self.is_running():
            self.logger.info("llama.cpp server already running")
            return
        
        # Ensure binary and model exist
        binary = self._ensure_binary()
        model = self._ensure_model()
        
        # Build command
        cmd = [
            str(binary),
            "-m", str(model),
            "--port", str(self.port),
            "--host", "127.0.0.1",
            "-c", str(self.settings.llamacpp_context_size),
            "--log-disable",  # Reduce log spam
        ]
        
        # Add Vulkan support
        if self.settings.llamacpp_use_vulkan:
            cmd.extend(["-ngl", str(self.settings.llamacpp_n_gpu_layers)])
            self.logger.info(f"Enabling Vulkan with {self.settings.llamacpp_n_gpu_layers} GPU layers")
        else:
            self.logger.info("Running in CPU-only mode")
        
        # Set environment
        env = os.environ.copy()
        if self.settings.llamacpp_use_vulkan:
            env["GGML_VULKAN_DEVICE"] = "0"
            # For AMD Renoir
            env["HSA_OVERRIDE_GFX_VERSION"] = "9.0.0"
        
        self.logger.info(f"Starting llama.cpp server...")
        self.logger.debug(f"Command: {' '.join(cmd)}")
        
        # Start process
        self.process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for server to be ready
        self.logger.info("Waiting for server to start...")
        for i in range(30):
            time.sleep(1)
            if self.is_running():
                self.logger.info(f"✅ llama.cpp server ready on port {self.port}")
                self.logger.info(f"Model: {model.name}")
                return
        
        # Check if process crashed
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(
                f"llama.cpp server failed to start:\n"
                f"STDOUT: {stdout[-500:] if stdout else 'empty'}\n"
                f"STDERR: {stderr[-500:] if stderr else 'empty'}"
            )
        
        raise RuntimeError("llama.cpp server did not respond in time")
    
    def stop(self):
        """Stop llama.cpp server."""
        if self.process:
            self.logger.info("Stopping llama.cpp server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning("Force killing llama.cpp server")
                self.process.kill()
                self.process.wait()
            self.process = None
            self.logger.info("llama.cpp server stopped")
