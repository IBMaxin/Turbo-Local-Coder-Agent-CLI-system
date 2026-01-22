"""llama.cpp Server Manager - Handles starting/stopping llama.cpp server."""
from __future__ import annotations

import logging
import os
import subprocess
import time
import signal
import atexit
import requests
from pathlib import Path
from typing import Optional

from .config import Settings


class LlamaCppServer:
    """Manages llama.cpp server process with optimizations."""
    
    _instance: Optional['LlamaCppServer'] = None
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger("LlamaCppServer")
        self.process: Optional[subprocess.Popen] = None
        self.port = settings.llamacpp_port
        self.model_path = Path(settings.llamacpp_model_path)
        
        # Register cleanup on exit
        if LlamaCppServer._instance is None:
            LlamaCppServer._instance = self
            atexit.register(self._cleanup)
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def _cleanup(self):
        """Cleanup on exit."""
        if self.process:
            self.stop()
    
    def is_running(self) -> bool:
        """Check if server is running and responding."""
        if not self.process or self.process.poll() is not None:
            return False
        
        # Quick health check
        try:
            resp = requests.get(f"http://127.0.0.1:{self.port}/health", timeout=1)
            return resp.status_code == 200
        except (requests.RequestException, ConnectionError):
            return False
    
    def _find_llamacpp_binary(self) -> Optional[Path]:
        """Find llama.cpp server binary."""
        # Check environment variable first
        env_binary = os.getenv("LLAMACPP_BINARY_PATH")
        if env_binary:
            binary_path = Path(env_binary)
            if binary_path.exists():
                self.logger.info(f"Using binary from LLAMACPP_BINARY_PATH: {binary_path}")
                return binary_path
        
        # Check common locations
        possible_paths = [
            Path("/home/bj/llama.cpp/llama-server"),
            Path("/home/bj/llama.cpp/build/bin/llama-server"),
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
    
    def _ensure_binary(self) -> Path:
        """Ensure llama.cpp binary exists."""
        binary = self._find_llamacpp_binary()
        if not binary:
            raise FileNotFoundError(
                "llama-server binary not found. Install it at:\n"
                "  /home/bj/llama.cpp/llama-server\n"
                "Or set LLAMACPP_BINARY_PATH environment variable."
            )
        return binary
    
    def _ensure_model(self) -> Path:
        """Ensure model file exists."""
        if self.model_path.exists():
            self.logger.info(f"Using model: {self.model_path}")
            return self.model_path
        
        raise FileNotFoundError(
            f"Model not found at {self.model_path}.\n"
            "Available models:\n"
            "  - /home/bj/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf\n"
            "  - /home/bj/models/Phi-3-mini-4k-instruct-q4.gguf\n"
            "Set LLAMACPP_MODEL_PATH in .env to the correct path."
        )
    
    def start(self):
        """Start llama.cpp server with optimizations."""
        if self.is_running():
            self.logger.info("llama.cpp server already running")
            return
        
        # Ensure binary and model exist
        binary = self._ensure_binary()
        model = self._ensure_model()
        
        # Build optimized command
        cmd = [
            str(binary),
            "-m", str(model),
            "--port", str(self.port),
            "--host", "127.0.0.1",
            "-c", str(self.settings.llamacpp_context_size),
            "--log-disable",  # Reduce log spam
            "-fa",  # Flash attention (faster)
            "-cb",  # Continuous batching
            "--cache-prompt",  # Cache prompts for speed
            "-np", "4",  # Parallel requests
        ]
        
        # Add GPU layers if Vulkan enabled
        if self.settings.llamacpp_use_vulkan:
            cmd.extend(["-ngl", str(self.settings.llamacpp_n_gpu_layers)])
            self.logger.info(f"🔥 Vulkan enabled: {self.settings.llamacpp_n_gpu_layers} GPU layers")
        else:
            self.logger.info("💻 CPU-only mode")
        
        # Set environment
        env = os.environ.copy()
        if self.settings.llamacpp_use_vulkan:
            env["GGML_VULKAN_DEVICE"] = "0"
            env["HSA_OVERRIDE_GFX_VERSION"] = "9.0.0"  # AMD Renoir fix
        
        self.logger.info("Starting llama.cpp server...")
        self.logger.debug(f"Command: {' '.join(cmd)}")
        
        # Start process
        try:
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,  # Suppress output
                stderr=subprocess.PIPE,
                text=True
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start llama.cpp: {e}")
        
        # Wait for server to be ready
        self.logger.info("Waiting for server startup...")
        for i in range(30):
            time.sleep(1)
            if self.is_running():
                self.logger.info(f"✅ llama.cpp ready on port {self.port}")
                self.logger.info(f"📦 Model: {model.name}")
                return
            
            # Check if process crashed
            if self.process.poll() is not None:
                _, stderr = self.process.communicate()
                raise RuntimeError(
                    f"llama.cpp crashed during startup:\n"
                    f"Error: {stderr[-1000:] if stderr else 'No error output'}"
                )
        
        # Timeout
        self.stop()
        raise RuntimeError("llama.cpp server did not start within 30 seconds")
    
    def stop(self):
        """Stop llama.cpp server gracefully."""
        if not self.process:
            return
        
        self.logger.info("Stopping llama.cpp server...")
        
        try:
            # Try graceful shutdown first
            self.process.terminate()
            self.process.wait(timeout=5)
            self.logger.info("Server stopped gracefully")
        except subprocess.TimeoutExpired:
            # Force kill if needed
            self.logger.warning("Force killing server...")
            self.process.kill()
            self.process.wait()
            self.logger.info("Server force stopped")
        except Exception as e:
            self.logger.error(f"Error stopping server: {e}")
        finally:
            self.process = None
