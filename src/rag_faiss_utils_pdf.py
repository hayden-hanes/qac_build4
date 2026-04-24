import os
import pickle
import numpy as np
from pathlib import Path
from openai import OpenAI

def build_rag_chunks(knowledge_dir):
    """Scans the directory for .md files and returns a list of text chunks."""
    chunks = []
    knowledge_path = Path(knowledge_dir)
    for md_file in knowledge_path.glob("**/*.md"):
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
            # Split by paragraphs to create chunks
            file_chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 10]
            chunks.extend(file_chunks)
    return chunks

def build_faiss_index(chunks, embedding_model="text-embedding-3-small"):
    """Fetches embeddings from OpenAI and returns a 'Mock' index (numpy array)."""
    client = OpenAI() # Assumes OPENAI_API_KEY is in your .env
    
    print(f"Requesting embeddings for {len(chunks)} chunks...")
    response = client.embeddings.create(input=chunks, model=embedding_model)
    
    embeddings = [data.embedding for data in response.data]
    index = np.array(embeddings).astype('float32')
    
    return index, None

def save_faiss_index(knowledge_dir, index, chunks, embedding_model):
    """Saves the numpy index and chunks to the files the agent expects."""
    index_path = "rag_faiss.index"
    meta_path = "rag_chunks.pkl"
    
    # Save the numpy array (the 'index')
    with open(index_path, "wb") as f:
        pickle.dump(index, f)
        
    # Save the text chunks
    with open(meta_path, "wb") as f:
        pickle.dump(chunks, f)
        
    return index_path, meta_path

def load_rag_index(index_path, pkl_path):
    """Used by the agent to load the data back in."""
    with open(index_path, "rb") as f:
        index = pickle.load(f)
    with open(pkl_path, "rb") as f:
        chunks = pickle.load(f)
    return index, chunks

def format_rag_context(chunks):
    """Formats a list of text chunks into a single numbered string for the prompt."""
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"--- Chunk {i+1} ---\n{chunk}\n\n"
    return context.strip()