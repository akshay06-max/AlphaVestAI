"""
ChromaDB vectorstore — Module 4.
"""
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embeddings


def build_vectorstore(chunks, persist_dir="data/chroma_db"):
    return Chroma.from_documents(chunks, get_embeddings(), persist_directory=persist_dir)


def get_retriever(vectorstore, k: int = 4):
    return vectorstore.as_retriever(search_kwargs={"k": k})
