import os
import sys
import pandas as pd
import hashlib
import glob
import json

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag import add_documents

MAX_RECORDS_PER_FILE = 2000

def parse_gorilla(df):
    """Parses Gorilla OpenFunctions parquet."""
    docs, metas, ids = [], [], []
    for _, row in df.head(MAX_RECORDS_PER_FILE).iterrows():
        try:
            tools = str(row['tools'])
            messages = row['messages']
            
            user_msg = next((m for m in messages if m['role'] == 'user'), None)
            assistant_msg = next((m for m in messages if m['role'] == 'assistant'), None)
            
            if not user_msg or not assistant_msg: continue
            
            instruction = f"Available Tools: {tools}\n\nTask: {user_msg['content']}"
            response = assistant_msg['content']
            
            doc_id = hashlib.md5(f"{instruction}_{response}".encode('utf-8')).hexdigest()
            docs.append(instruction)
            metas.append({"type": "few_shot", "persona": "askdeepakai", "ideal_response": response})
            ids.append(doc_id)
        except Exception as e:
            continue
    return docs, metas, ids

def parse_swe_bench(df):
    """Parses SWE-bench parquet."""
    docs, metas, ids = [], [], []
    for _, row in df.head(MAX_RECORDS_PER_FILE).iterrows():
        try:
            instruction = row['problem_statement']
            response = row['patch']
            
            if not instruction or not response: continue
            
            doc_id = hashlib.md5(f"{instruction}_{response}".encode('utf-8')).hexdigest()
            docs.append(instruction)
            metas.append({"type": "few_shot", "persona": "askdeepakai", "ideal_response": response})
            ids.append(doc_id)
        except Exception as e:
            continue
    return docs, metas, ids

def parse_toolbench(df):
    """Parses ToolBench parquet."""
    docs, metas, ids = [], [], []
    for _, row in df.head(MAX_RECORDS_PER_FILE).iterrows():
        try:
            conversations = row['conversations']
            from_arr = conversations['from']
            val_arr = conversations['value']
            
            user_idx = -1
            for i, role in enumerate(from_arr):
                if role == 'user':
                    user_idx = i
                    break
                    
            if user_idx == -1 or user_idx + 1 >= len(val_arr): continue
            
            instruction = val_arr[user_idx]
            response = val_arr[user_idx + 1] # assistant or function
            
            doc_id = hashlib.md5(f"{instruction}_{response}".encode('utf-8')).hexdigest()
            docs.append(instruction)
            metas.append({"type": "few_shot", "persona": "askdeepakai", "ideal_response": response})
            ids.append(doc_id)
        except Exception as e:
            continue
    return docs, metas, ids

def parse_open_assistant(df):
    """Parses OpenAssistant parquet."""
    docs, metas, ids = [], [], []
    
    # OpenAssistant is a tree. We pair prompter messages with their child assistant replies.
    # We will build a simple map of parent_id -> child message
    
    # Filter for top quality English/Code if needed, but we'll take raw for now
    df_limited = df.head(MAX_RECORDS_PER_FILE * 2) # Grab more to ensure pairs
    
    # Map of message_id to text for prompters
    prompters = {}
    for _, row in df_limited[df_limited['role'] == 'prompter'].iterrows():
        prompters[row['message_id']] = row['text']
        
    for _, row in df_limited[df_limited['role'] == 'assistant'].iterrows():
        parent_id = row['parent_id']
        if parent_id in prompters:
            instruction = prompters[parent_id]
            response = row['text']
            
            doc_id = hashlib.md5(f"{instruction}_{response}".encode('utf-8')).hexdigest()
            docs.append(instruction)
            metas.append({"type": "few_shot", "persona": "chat", "ideal_response": response})
            ids.append(doc_id)
            
            # Remove to only get the first/best response for each prompt
            del prompters[parent_id]
            
            if len(docs) >= MAX_RECORDS_PER_FILE:
                break
                
    return docs, metas, ids


def ingest_datasets(dataset_dir):
    all_docs = []
    all_metas = []
    all_ids = []
    seen_ids = set()
    
    parquet_files = glob.glob(os.path.join(dataset_dir, '*/*.parquet'))
    
    for file in parquet_files:
        print(f"Processing {file}...")
        try:
            df = pd.read_parquet(file)
            cols = list(df.columns)
            
            docs, metas, ids = [], [], []
            
            if 'tools' in cols and 'messages' in cols:
                print("  -> Identified as Gorilla OpenFunctions")
                docs, metas, ids = parse_gorilla(df)
            elif 'problem_statement' in cols and 'patch' in cols:
                print("  -> Identified as SWE-bench")
                docs, metas, ids = parse_swe_bench(df)
            elif 'conversations' in cols:
                print("  -> Identified as ToolBench")
                docs, metas, ids = parse_toolbench(df)
            elif 'parent_id' in cols and 'role' in cols:
                print("  -> Identified as OpenAssistant")
                docs, metas, ids = parse_open_assistant(df)
            else:
                print(f"  -> Unknown schema: {cols}")
                continue
                
            for d, m, i in zip(docs, metas, ids):
                if i not in seen_ids:
                    seen_ids.add(i)
                    all_docs.append(d)
                    all_metas.append(m)
                    all_ids.append(i)
                    
            print(f"  -> Extracted {len(docs)} records.")
        except Exception as e:
            print(f"Error processing {file}: {e}")
            
    if all_docs:
        print(f"\nIngesting {len(all_docs)} total records into ChromaDB...")
        # Add in batches to avoid overwhelming ChromaDB
        batch_size = 500
        for i in range(0, len(all_docs), batch_size):
            end_idx = min(i + batch_size, len(all_docs))
            add_documents(all_docs[i:end_idx], all_metas[i:end_idx], all_ids[i:end_idx])
            print(f"  Batch {i//batch_size + 1}: Ingested {end_idx - i} records.")
        print("Done!")
    else:
        print("No valid records found to ingest.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        dataset_dir = sys.argv[1]
    else:
        dataset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets")
        
    if not os.path.exists(dataset_dir):
        print(f"Directory not found: {dataset_dir}")
        sys.exit(1)
        
    ingest_datasets(dataset_dir)
