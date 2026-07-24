import os
from llama_cpp import Llama
model_path = os.path.join(os.path.abspath("."), "Base Offline Model", "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf")
print(f"Loading {model_path}")
try:
    llm = Llama(model_path=model_path, n_gpu_layers=-1, n_ctx=4096, verbose=True)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
