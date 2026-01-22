# llama.cpp Setup Guide

## Quick Start (You Already Have llama.cpp!)

You have llama.cpp installed at `/home/bj/llama.cpp` with 3 models. Let's use **Phi-3-mini** (best quality):

### 1️⃣ Update Your .env

```bash
cd ~/Turbo-Local-Coder-Agent-CLI-system

# Backup current .env
cp .env .env.ollama-backup

# Copy the llama.cpp template
cp .env.llamacpp-example .env

# Edit to use Phi-3-mini
nano .env
```

**Key settings to verify:**
```bash
BACKEND=llamacpp
LLAMACPP_BINARY_PATH=/home/bj/llama.cpp/llama-server
LLAMACPP_MODEL_PATH=/home/bj/llama.cpp/models/Phi-3-mini-4k-instruct-q4.gguf
LLAMACPP_PORT=8080
LLAMACPP_USE_VULKAN=1
LLAMACPP_N_GPU_LAYERS=32
```

### 2️⃣ Test It

```bash
git pull origin main  # Get latest patches

# Run a test
time python3 -m agent.team.workflow
```

**Expected output:**
```
[BACKEND] Using llama.cpp backend
✅ llama.cpp server ready on port 8080
Model: Phi-3-mini-4k-instruct-q4.gguf
[PLAN] Planning phase...
...
```

---

## Model Comparison

### Your Available Models:

| Model | Size | Speed (CPU) | Speed (Vulkan) | Quality | Recommended For |
|:------|:-----|:------------|:---------------|:--------|:----------------|
| **Phi-3-mini** | 3.8B | 8-12 tok/s | 25-40 tok/s | ⭐⭐⭐⭐⭐ | **Production** |
| SmolLM2 | 1.7B | 15-25 tok/s | 50-80 tok/s | ⭐⭐⭐ | Quick tasks |
| FunctionGemma | 270M | 40-60 tok/s | 100+ tok/s | ⭐⭐ | Experiments |

**Recommendation:** Start with **Phi-3-mini** for best results!

---

## Switching Models

To try a different model, just edit your `.env`:

### For SmolLM2 (faster, less capable):
```bash
LLAMACPP_MODEL_PATH=/home/bj/llama.cpp/models/SmolLM2-1.7B-Instruct-Q4_K_M.gguf
PLANNER_MODEL=smollm2
CODER_MODEL=smollm2
```

### For FunctionGemma (very fast, limited):
```bash
LLAMACPP_MODEL_PATH=/home/bj/llama.cpp/models/functiongemma-270m-it-Q4_K_M.gguf
PLANNER_MODEL=functiongemma
CODER_MODEL=functiongemma
```

Then restart: `python3 -m agent.team.workflow`

---

## Enable Vulkan (GPU Acceleration)

### Check If Vulkan Works:

```bash
# Install Vulkan tools
sudo apt install mesa-vulkan-drivers vulkan-tools

# Check GPU detection
vulkaninfo | grep -i "device name"
# Should show: AMD Radeon Graphics (RENOIR)

# Set AMD override
export HSA_OVERRIDE_GFX_VERSION=9.0.0
echo 'export HSA_OVERRIDE_GFX_VERSION=9.0.0' >> ~/.bashrc
```

### Test Vulkan with llama.cpp:

```bash
cd /home/bj/llama.cpp

./llama-server \
  -m models/Phi-3-mini-4k-instruct-q4.gguf \
  --port 8080 \
  -ngl 32  # GPU layers

# In another terminal:
curl http://127.0.0.1:8080/health
# Should return: {"status":"ok"}
```

If you see **"using Vulkan"** in the logs, it's working! 🚀

---

## Performance Expectations

### With Phi-3-mini:

| Configuration | Time for Simple Task | Tokens/sec |
|:--------------|:--------------------|:-----------|
| CPU only | ~120-180s | 8-12 |
| **CPU + Vulkan** | **60-100s** | **25-40** |

### Ollama vs llama.cpp:

- **Ollama (Phi-4-mini)**: 148s
- **llama.cpp (Phi-3-mini, CPU)**: ~140-160s
- **llama.cpp (Phi-3-mini, Vulkan)**: **~70-100s** 🔥

---

## Troubleshooting

### Server Won't Start:

```bash
# Check if port is in use
sudo lsof -i :8080

# Kill existing server
pkill llama-server

# Try manual start to see errors
/home/bj/llama.cpp/llama-server \
  -m /home/bj/llama.cpp/models/Phi-3-mini-4k-instruct-q4.gguf \
  --port 8080
```

### Vulkan Not Working:

```bash
# Install missing packages
sudo apt install libvulkan1 mesa-vulkan-drivers vulkan-tools

# Check driver
ls /usr/share/vulkan/icd.d/
# Should see: radeon_icd.x86_64.json

# Test Vulkan
vulkaninfo | grep "apiVersion"
```

### Model Not Found:

```bash
# List your models
ls -lh /home/bj/llama.cpp/models/

# Update .env with exact filename
LLAMACPP_MODEL_PATH=/home/bj/llama.cpp/models/Phi-3-mini-4k-instruct-q4.gguf
```

---

## Advanced: Download More Models

Want to try other models? Download from Hugging Face:

```bash
# Install huggingface-cli
pip install huggingface-hub

# Download Qwen2.5-Coder (7B, excellent for coding)
huggingface-cli download \
  bartowski/Qwen2.5-Coder-7B-Instruct-GGUF \
  Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf \
  --local-dir /home/bj/llama.cpp/models/

# Download DeepSeek-Coder (6.7B)
huggingface-cli download \
  TheBloke/deepseek-coder-6.7B-instruct-GGUF \
  deepseek-coder-6.7b-instruct.Q4_K_M.gguf \
  --local-dir /home/bj/llama.cpp/models/
```

Then update your `.env` to use the new model!

---

## Summary

**What you need to do:**

1. ✅ Pull latest changes: `git pull origin main`
2. ✅ Copy .env template: `cp .env.llamacpp-example .env`
3. ✅ Edit `.env` to point to your models
4. ✅ Test: `python3 -m agent.team.workflow`
5. 🚀 Enable Vulkan for 2-3x speedup!

**Your setup is already 90% done!** Just need to configure the `.env` file. 🎯
