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
        # Check common locations
        possible_paths = [
            Path("./llama.cpp/llama-server"),
            Path("./llama-server"),
            Path("/usr/local/bin/llama-server"),
            Path("/usr/bin/llama-server"),
            Path.home() / "llama.cpp" / "llama-server",
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_file():
                return path
        
        # Check PATH
        import shutil
        binary = shutil.which("llama-server")
        if binary:
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
            self.logger.info(f"Found llama.cpp at {binary}")
            return binary
        
        self.logger.warning("llama.cpp binary not found, downloading...")
        return self._download_binary()
    
    def _ensure_model(self) -> Path:
        """Ensure model file exists, download if needed."""
        if self.model_path.exists():
            self.logger.info(f"Using model: {self.model_path}")
            return self.model_path
        
        # Auto-download from Hugging Face
        self.logger.info(f"Model not found at {self.model_path}, downloading...")
        
        from huggingface_hub import hf_hub_download
        
        # Default to Phi-4-mini Q4_K_M
        repo_id = "microsoft/phi-4-mini-gguf"
        filename = "phi-4-mini-Q4_K_M.gguf"
        
        models_dir = Path("./models")
        models_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Downloading {filename} from {repo_id}...")
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=models_dir,
            local_dir_use_symlinks=False
        )
        
        self.model_path = Path(downloaded_path)
        self.logger.info(f"Model downloaded to {self.model_path}")
        return self.model_path
    
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
        ]
        
        # Add Vulkan support
        if self.settings.llamacpp_use_vulkan:
            cmd.extend(["-ngl", str(self.settings.llamacpp_n_gpu_layers)])
            self.logger.info(f"Enabling Vulkan with {self.settings.llamacpp_n_gpu_layers} GPU layers")
        
        # Set environment
        env = os.environ.copy()
        if self.settings.llamacpp_use_vulkan:
            env["GGML_VULKAN_DEVICE"] = "0"
        
        self.logger.info(f"Starting llama.cpp server: {' '.join(cmd)}")
        
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
                self.logger.info(f"llama.cpp server ready on port {self.port}")
                return
        
        # Check if process crashed
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(f"llama.cpp server failed to start:\nSTDOUT: {stdout}\nSTDERR: {stderr}")
        
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
