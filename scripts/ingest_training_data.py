import os
import sys
import json
import uuid

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag import add_documents, collection

def ingest_json_file(file_path: str, persona: str):
    """
    Ingests a JSONL file of training data (Chat format) into ChromaDB.
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    documents = []
    metadatas = []
    ids = []

    seen_ids = set()

    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f):
            if not line.strip():
                continue
            
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                print(f"Warning: Skipping invalid JSON on line {line_num+1}")
                continue
            
            # Check if it's the standard Chat format (messages array)
            if "messages" in item:
                messages = item["messages"]
                
                # Extract the user request (task)
                user_msg = next((m for m in messages if m.get("role") == "user"), None)
                if not user_msg:
                    continue
                
                # Handle lists of content parts (multimodal) or string content
                content = user_msg.get("content", "")
                if isinstance(content, list):
                    # extract the text part
                    task_instruction = next((c.get("text") for c in content if c.get("type") == "text"), str(content))
                else:
                    task_instruction = content
                
                # Extract the ideal assistant response
                assistant_msg = next((m for m in messages if m.get("role") == "assistant"), None)
                if not assistant_msg:
                    continue
                    
                ideal_response = assistant_msg.get("content", "")
            else:
                # Fallback for generic format
                task_instruction = item.get("instruction") or item.get("input") or str(item)
                ideal_response = item.get("output") or item.get("response") or json.dumps(item)

            import hashlib
            # Use deterministic hash of the instruction + response to prevent duplicates
            hash_input = f"{task_instruction}_{ideal_response}".encode('utf-8')
            doc_id = hashlib.md5(hash_input).hexdigest()
            
            if doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)
            
            documents.append(task_instruction)
            metadatas.append({
                "type": "few_shot",
                "persona": persona,
                "ideal_response": ideal_response
            })
            ids.append(doc_id)
        
    if documents:
        add_documents(documents, metadatas, ids)
        print(f"Successfully ingested {len(documents)} training records for {persona} into DeepakLLM.")
    else:
        print("No valid records found to ingest.")

if __name__ == "__main__":
    print("DeepakLLM Data Ingestion Script")
    print("Usage: Update this script to match your JSON keys, then run:")
    print("python scripts/ingest_training_data.py <path_to_json> <echo|askdeepakai>")
    
    if len(sys.argv) > 2:
        file_path = sys.argv[1]
        persona = sys.argv[2]
        ingest_json_file(file_path, persona)
