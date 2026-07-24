import requests
import json
import time

API_URL = "http://localhost:8003/v1"

def test_echo():
    print("\n--- Testing Echo Persona ---")
    payload = {
        "client_id": "echo",
        "messages": [
            {"role": "user", "content": "I have a meeting in 10 minutes, what should I do?"}
        ],
        "stream": False,
        "use_rag": False
    }
    
    start_time = time.time()
    response = requests.post(f"{API_URL}/chat/completions", json=payload)
    end_time = time.time()
    
    if response.status_code == 200:
        print(f"Response ({end_time - start_time:.2f}s):")
        print(response.json()["choices"][0]["message"]["content"])
    else:
        print(f"Error: {response.text}")

def test_askdeepakai_stream():
    print("\n--- Testing AskDeepakAI Persona (Streaming) ---")
    payload = {
        "client_id": "askdeepakai",
        "messages": [
            {"role": "user", "content": "Write a python function to compute the Fibonacci sequence efficiently using memoization. Explain the time complexity."}
        ],
        "stream": True,
        "use_rag": False
    }
    
    response = requests.post(f"{API_URL}/chat/completions", json=payload, stream=True)
    if response.status_code == 200:
        print("Streaming response:")
        for line in response.iter_lines():
            if line:
                print(line.decode('utf-8'), end="", flush=True)
        print()
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    print("Testing DeepakLLM API...")
    test_echo()
    time.sleep(1)
    test_askdeepakai_stream()
