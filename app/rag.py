import chromadb
from chromadb.utils import embedding_functions
import os

# Initialize ChromaDB locally
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_data")
chroma_client = chromadb.PersistentClient(path=DB_DIR)

# We use a default lightweight sentence transformer for embeddings
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Get or create the collection for DeepakLLM's knowledge base
collection = chroma_client.get_or_create_collection(
    name="deepak_knowledge",
    embedding_function=sentence_transformer_ef
)

def add_documents(documents: list[str], metadatas: list[dict], ids: list[str]):
    """
    Add custom documents to the vector database for RAG.
    """
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

def search_context(query: str, n_results: int = 3) -> list[dict]:
    """
    Search the vector database for context relevant to the query.
    Returns a list of dicts with 'document' and 'metadata'.
    """
    if collection.count() == 0:
        return []
        
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count())
    )
    
    formatted_results = []
    if results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
        for doc, meta in zip(docs, metas):
            formatted_results.append({"document": doc, "metadata": meta})
            
    return formatted_results
