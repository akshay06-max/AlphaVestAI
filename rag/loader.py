"""Document loading + chunking for Financial RAG — Module 4."""
import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def load_and_split(file_path: str, doc_type: str = "Annual Report", chunk_size: int = 1000, chunk_overlap: int = 150):
    """Load and chunk financial documents (PDF, TXT, CSV) with rich metadata."""
    ext = os.path.splitext(file_path)[1].lower()
    docs = []
    
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
        docs = loader.load()
    elif ext == ".csv":
        loader = CSVLoader(file_path)
        docs = loader.load()
    elif ext in (".txt", ".md"):
        loader = TextLoader(file_path, encoding="utf-8")
        docs = loader.load()
    else:
        # Fallback raw text loader
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        docs = [Document(page_content=text, metadata={"source": file_path})]

    # Enrich metadata
    base_name = os.path.basename(file_path)
    for d in docs:
        d.metadata["doc_type"] = doc_type
        d.metadata["filename"] = base_name

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(docs)
