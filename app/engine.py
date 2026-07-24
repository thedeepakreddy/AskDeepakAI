import os
import re
import subprocess
from typing import List, Dict, Generator
from dotenv import load_dotenv
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup
from app.personas import get_persona
from app.rag import search_context
from app.python_executor import execute_python_code
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None
from groq import Groq

load_dotenv()

# Global model cache to avoid reloading the 4.7GB file every request
_llama_model = None

def get_llm():
    global _llama_model
    if _llama_model is None:
        if Llama is None:
            raise ImportError("llama-cpp-python is not installed. Offline models are unavailable in this environment.")
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Base Offline Model", "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf")
        print(f"Loading local model from {model_path}...")
        _llama_model = Llama(
            model_path=model_path,
            n_gpu_layers=25, # Leave 7 layers on CPU to strictly prevent Apple Metal VRAM crashes
            n_ctx=2048,
            verbose=False
        )
        print("Model loaded successfully.")
    return _llama_model

def format_context(context_docs: List[Dict]) -> str:
    """Formats retrieved documents and metadata into Few-Shot examples or standard context."""
    if not context_docs:
        return ""
        
    context_str = "\n\n--- PAST EXAMPLES / ADDITIONAL CONTEXT ---\n"
    context_str += "Use the following successful past examples to guide your response format and logic if they are relevant:\n\n"
    
    for i, doc in enumerate(context_docs):
        meta = doc.get("metadata", {})
        if meta.get("type") == "few_shot":
            context_str += f"[Example {i+1}]\n"
            context_str += f"User Request: {doc.get('document')}\n"
            context_str += f"Ideal Response: {meta.get('ideal_response')}\n\n"
        else:
            context_str += f"[Context {i+1}]\n{doc.get('document')}\n\n"
            
    # Hard cap the RAG context length so we don't blow the context window
    if len(context_str) > 1500:
        context_str = context_str[:1500] + "\n...[Context Truncated]"
        
    return context_str

def execute_command(command: str) -> str:
    """Securely executes a shell command and returns the output."""
    try:
        # Run command securely with timeout
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        output = result.stdout
        if result.stderr:
            output += "\nError: " + result.stderr
        return output.strip() if output else "Command executed successfully with no output."
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Execution error: {str(e)}"

def execute_web_search(query: str) -> str:
    """Performs a live web search using DuckDuckGo and scrapes the top result."""
    try:
        results = list(DDGS().text(query, max_results=3))
        if not results:
            return "No results found."
        
        output = "Search Results:\n"
        for i, r in enumerate(results):
            output += f"{i+1}. Title: {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}\n\n"
            
        # Scrape the first link to get detailed text
        first_url = results[0].get('href')
        if first_url:
            output += f"\n--- Scraped Content from Top Result ({first_url}) ---\n"
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                response = requests.get(first_url, headers=headers, timeout=8)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for script in soup(["script", "style"]):
                        script.decompose()
                    text = soup.get_text(separator=' ', strip=True)
                    output += text[:2500] + ("..." if len(text) > 2500 else "")
                else:
                    output += f"Failed to fetch page content. HTTP {response.status_code}"
            except Exception as e:
                output += f"Failed to scrape page: {str(e)}"
                
        return output.strip()
    except Exception as e:
        return f"Web search error: {str(e)}"

def generate_response(client_id: str, messages: List[Dict[str, str]], use_rag: bool = True) -> str:
    """
    Generates a full response from the LLM, with an agentic loop for tool execution.
    """
    system_prompt = get_persona(client_id)
    
    # Extract the last user message to use for RAG search
    last_user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    
    context = ""
    if use_rag and last_user_message:
        context_docs = search_context(last_user_message)
        context = format_context(context_docs)
    
    # Prepare the message payload
    full_system_prompt = system_prompt + context
    
    # Keep only the last 10 messages to prevent blowing the context window
    truncated_messages = messages[-10:] if len(messages) > 10 else messages
    
    current_messages = [{"role": "system", "content": full_system_prompt}] + truncated_messages

    max_iterations = 3
    final_response = ""

    is_offline = (client_id.lower() == "pluto_lite")
    
    global _llama_model
    if not is_offline:
        # Free up the Mac's RAM by unloading the local model when switching to Cloud!
        if _llama_model is not None:
            print("Unloading local model to free up RAM...")
            del _llama_model
            _llama_model = None
            
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    else:
        llm = get_llm()

    for iteration in range(max_iterations):
        if not is_offline:
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=current_messages,
                    temperature=0.7,
                    max_tokens=2048,
                    top_p=0.9
                )
                reply = response.choices[0].message.content
            except Exception as e:
                if "rate limit" in str(e).lower() or "429" in str(e):
                    response = groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=current_messages,
                        temperature=0.7,
                        max_tokens=2048,
                        top_p=0.9
                    )
                    reply = response.choices[0].message.content
                else:
                    raise e
        else:
            response = llm.create_chat_completion(
                messages=current_messages,
                temperature=0.7,
                max_tokens=2048,
                top_p=0.9
            )
            reply = response["choices"][0]["message"]["content"]
        
        
        # Check for [API_REQUEST]: <command> or [WEB_SEARCH]: <query> or [PYTHON_EXEC]: <code>
        api_match = re.search(r'\[API_REQUEST\]:\s*(.*)', reply)
        web_match = re.search(r'\[WEB_SEARCH\]:\s*(.*)', reply)
        python_match = re.search(r'\[PYTHON_EXEC\]:\s*```(?:python)?\s*(.*?)\s*```', reply, re.DOTALL)
        
        if python_match:
            code = python_match.group(1).strip()
            final_response += reply + "\n"
            
            tool_output = execute_python_code(code)
            
            current_messages.append({"role": "assistant", "content": reply})
            current_messages.append({
                "role": "user", 
                "content": f"Python Output:\n{tool_output}\nIf you generated a chart, remember to include the markdown link to it. Now provide the final response or continue analysis."
            })
            
            final_response += f"```\n[Executing Python Code]\n{tool_output}\n```\n\n"
        elif api_match:
            command = api_match.group(1).strip()
            final_response += reply + "\n"
            
            # Execute command
            tool_output = execute_command(command)
            
            # Append AI's reply and the tool output to messages
            current_messages.append({"role": "assistant", "content": reply})
            current_messages.append({
                "role": "user", 
                "content": f"Tool Output:\n{tool_output}\nNow provide the final response to the user."
            })
            
            final_response += f"```\n[Executing]: {command}\n{tool_output}\n```\n\n"
        elif web_match:
            query = web_match.group(1).strip()
            final_response += reply + "\n"
            
            # Execute web search
            tool_output = execute_web_search(query)
            
            # Append AI's reply and the search results to messages
            current_messages.append({"role": "assistant", "content": reply})
            current_messages.append({
                "role": "user", 
                "content": f"Web Search Output:\n{tool_output}\nNow provide the final response to the user using these search results."
            })
            
            result_count = len(tool_output.split('Title:')) - 1
            final_response += f"```\n[Web Search]: {query}\nFetched {result_count} live web results.\n```\n\n"
        else:
            final_response += reply
            break
            
    return final_response.strip()

def generate_response_stream(client_id: str, messages: List[Dict[str, str]], use_rag: bool = True) -> Generator[str, None, None]:
    """
    Generates a streaming response from the local LLM.
    """
    system_prompt = get_persona(client_id)
    
    last_user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    
    context = ""
    if use_rag and last_user_message:
        context_docs = search_context(last_user_message)
        context = format_context(context_docs)
            
    full_system_prompt = system_prompt + context
    
    # Keep only the last 10 messages to prevent blowing the context window
    truncated_messages = messages[-10:] if len(messages) > 10 else messages
    
    api_messages = [{"role": "system", "content": full_system_prompt}] + truncated_messages

    is_offline = (client_id.lower() == "pluto_lite")
    
    global _llama_model
    if not is_offline:
        # Free up the Mac's RAM by unloading the local model when switching to Cloud!
        if _llama_model is not None:
            print("Unloading local model to free up RAM...")
            del _llama_model
            _llama_model = None
            
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        try:
            stream = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=api_messages,
                temperature=0.7,
                max_tokens=2048,
                top_p=0.9,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e):
                stream = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=api_messages,
                    temperature=0.7,
                    max_tokens=2048,
                    top_p=0.9,
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
            else:
                yield f"Error connecting to Groq: {str(e)}"
    else:
        llm = get_llm()
        stream = llm.create_chat_completion(
            messages=api_messages,
            temperature=0.7,
            max_tokens=2048,
            top_p=0.9,
            stream=True
        )
        
        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta:
                yield delta["content"]
