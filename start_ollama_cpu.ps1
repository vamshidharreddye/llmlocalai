# Start Ollama in CPU-only mode by disabling CUDA
# This wrapper script ensures Ollama doesn't try to use the GPU

Write-Output "Starting Ollama in CPU-only mode..."

# Disable CUDA and all GPU libraries
$env:CUDA_VISIBLE_DEVICES = ""
$env:GGML_CUDA = "0"
$env:GGML_VK = "0"
$env:OLLAMA_NUM_GPU = "0"

# Ensure OLLAMA_DEBUG is off for cleaner output
$env:OLLAMA_DEBUG = ""

# Start Ollama
& 'C:\Users\VAMSHI\AppData\Local\Programs\Ollama\ollama.exe' serve
