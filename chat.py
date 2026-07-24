import requests
import json
import sys

API_URL = "http://localhost:8003/v1"

def print_colored(text, color_code):
    print(f"\033[{color_code}m{text}\033[0m", end="")

def main():
    print_colored("======================================\n", "36")
    print_colored("         DeepakLLM Terminal           \n", "36")
    print_colored("======================================\n", "36")
    print("Type 'exit' to quit. Type 'switch' to change persona.\n")

    current_persona = "askdeepakai"
    
    # Keep track of conversation history
    messages = []

    while True:
        try:
            user_input = input(f"\n\033[32mYou ({current_persona}):\033[0m ")
            if user_input.lower() in ['exit', 'quit']:
                break
            if user_input.lower() == 'switch':
                current_persona = "echo" if current_persona == "askdeepakai" else "askdeepakai"
                messages = [] # clear history on switch
                print_colored(f"Switched persona to: {current_persona}\n", "33")
                continue
            
            if not user_input.strip():
                continue

            messages.append({"role": "user", "content": user_input})
            
            payload = {
                "client_id": current_persona,
                "messages": messages,
                "stream": True,
                "use_rag": True
            }

            print_colored("\nDeepakLLM: ", "36")
            
            response = requests.post(f"{API_URL}/chat/completions", json=payload, stream=True)
            
            if response.status_code != 200:
                print_colored(f"Error: Server returned {response.status_code}\n", "31")
                print(response.text)
                messages.pop() # remove the failed message
                continue

            full_response = ""
            for line in response.iter_lines():
                if line:
                    chunk = line.decode('utf-8')
                    full_response += chunk
                    print_colored(chunk, "36")
                    sys.stdout.flush()
            
            print("\n")
            messages.append({"role": "assistant", "content": full_response})

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except requests.exceptions.ConnectionError:
            print_colored("\nError: Could not connect to DeepakLLM. Is the server running?", "31")
            break

if __name__ == "__main__":
    main()
