import pypdf
import chromadb
from llama_index.core import VectorStoreIndex, Document, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from config import GRAPH_STORE_DIR  # noqa: F401 - triggers Settings setup
from pathlib import Path
from typing import List


def load_pdf(path: str) -> List[Document]:
    reader = pypdf.PdfReader(path)
    pages: List[Document] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append(Document(text=text, metadata={"page": i + 1, "source": str(path)}))
    print(f"Extracted {len(pages)} pages from {path}")
    return pages


def load_pdfs_from_dir(directory: str) -> List[Document]:
    docs: List[Document] = []
    p = Path(directory)
    pdf_paths = list(p.rglob("*.pdf"))
    print(f"Found {len(pdf_paths)} PDF files under {directory}")
    for i, pdf_path in enumerate(pdf_paths, start=1):
        print(f"Processing file {i}/{len(pdf_paths)}: {pdf_path}")
        docs.extend(load_pdf(str(pdf_path)))
    return docs


def main() -> None:
    chroma_client = chromadb.PersistentClient(path="chroma_db/")
    chroma_collection = chroma_client.get_or_create_collection("documents")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    documents = load_pdfs_from_dir("data/")
    if not documents:
        print("No PDF documents found under data/; nothing to index.")
        return

    print(f"Starting indexing of {len(documents)} pages...")
    VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    print(f"Indexing complete: persisted {len(documents)} pages to chroma_db/")


if __name__ == "__main__":
    main()
