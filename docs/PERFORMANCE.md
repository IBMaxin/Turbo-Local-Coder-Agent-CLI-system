# Performance Optimization Guide

## Current Performance (Ollama + Phi-4-mini CPU)
- **Planning**: ~10-15s
- **Coding per iteration**: ~180-220s
- **Total for simple task**: 400-500s

## Quick Wins 🚀

### 1. Enable Vulkan GPU Acceleration (Recommended)
**Expected speedup: 3-5x faster**

Your AMD Renoir iGPU supports Vulkan! Enable it:

```bash
# Install Vulkan support
sudo apt install mesa-vulkan-drivers vulkan-tools
vulkaninfo | grep deviceName  # Verify GPU detected

# Pull Ollama with Vulkan
curl -fsSL https://ollama.com/install.sh | sh

# Set environment variable
export HSA_OVERRIDE_GFX_VERSION=9.0.0  # For AMD Renoir
```

Add to your `.env`:
```bash
OLLAMA_GPU_LAYERS=32
```

**Expected result**: 400s → **120-180s**

---

### 2. Switch to llama.cpp Backend
**Expected speedup: 2-4x faster**

llama.cpp is more optimized for CPU and Vulkan:

```bash
# Add to .env
BACKEND=llamacpp
LLAMACPP_USE_VULKAN=1
LLAMACPP_N_GPU_LAYERS=32
LLAMACPP_MODEL_PATH=./models/phi-4-mini-Q4_K_M.gguf
```

First run auto-downloads everything.

**Expected result**: 400s → **80-150s** (with Vulkan)

---

### 3. Reduce Max Steps
**Expected speedup: ~20% faster**

If your tasks are simple, reduce iterations:

```bash
# In .env
MAX_STEPS=15  # Default is 25
```

**Expected result**: 400s → **320-360s**

---

### 4. Use Smaller Context Window
**Expected speedup: ~15% faster**

Reduce context for faster processing:

```bash
# In .env (for llama.cpp)
LLAMACPP_CONTEXT_SIZE=2048  # Default is 4096
```

---

### 5. Backend Parameters Already Optimized ✅

The latest patches include:
- ✅ `temperature: 0.1` (faster, deterministic)
- ✅ `num_predict: 2048` (prevents truncation)
- ✅ `num_thread: 8` (uses more CPU cores)
- ✅ Stop tokens to end generation early
- ✅ `top_k: 40` for faster sampling

---

## Performance Comparison

| Configuration | Expected Time | Speedup |
|:--------------|:--------------|:--------|
| **Current (CPU only)** | 400-500s | 1x |
| CPU + Optimized params | 320-400s | 1.2x |
| CPU + llama.cpp | 250-350s | 1.5x |
| **Vulkan + Ollama** | 120-180s | **3x** |
| **Vulkan + llama.cpp** | 80-150s | **4-5x** 🚀 |

---

## Benchmark Your Setup

After optimizations, run:

```bash
time python3 -m agent.team.workflow
```

Look for these metrics in output:
```
[DEBUG] Generated 547 tokens at 12.3 tok/s
```

**Target speeds:**
- CPU: 5-8 tok/s
- Vulkan: 15-30 tok/s
- With good GPU: 40-80 tok/s

---

## Troubleshooting Slow Performance

### Check if Vulkan is working:
```bash
vulkaninfo | grep -i "device name"
# Should show: AMD Radeon Graphics (RENOIR)
```

### Check Ollama GPU usage:
```bash
ollama ps
# Should show GPU: YES
```

### Monitor resource usage:
```bash
htop  # Check CPU usage
radeontop  # Check GPU usage (install: sudo apt install radeontop)
```

---

## Advanced: Quantization

If still too slow, use more aggressive quantization:

```bash
# Instead of Q4_K_M, try Q3_K_M (smaller, faster)
ollama pull phi4-mini:q3_K_M

# Update .env
PLANNER_MODEL=phi4-mini:q3_K_M
CODER_MODEL=phi4-mini:q3_K_M
```

**Trade-off**: ~30% faster, slight quality reduction

---

## Summary

For **maximum speed on your hardware**:

1. ✅ Pull latest optimizations: `git pull origin main`
2. 🔥 Enable Vulkan (see section 1)
3. 🚀 Switch to llama.cpp backend (see section 2)
4. ⚙️ Set `MAX_STEPS=15` in `.env`

**Expected final performance**: **80-150 seconds** (5x faster than current)
