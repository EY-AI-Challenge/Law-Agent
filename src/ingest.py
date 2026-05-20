import os
import time
import pypdf
from llama_index.core import PropertyGraphIndex, Document
from llama_index.core.indices.property_graph import (  # type: ignore[import-untyped]
    ImplicitPathExtractor,
    SimpleLLMPathExtractor,
)
from llama_index.llms.groq import Groq  # type: ignore[import-untyped]
from config import CIVIL_GRAPH_STORE_DIR, LABOUR_GRAPH_STORE_DIR
from pathlib import Path
from typing import List

# Groq free tier: 6000 TPM. Each SimpleLLMPathExtractor call uses ~1000-1800 tokens,
# so we must wait at least 15s between page insertions to stay within the window.
RATE_LIMIT_SLEEP = 15.0


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


def build_index(directory: str, persist_dir: str, groq_llm) -> None:
    documents = load_pdfs_from_dir(directory)
    if not documents:
        print(f"No PDF documents found under {directory}; skipping.")
        return

    kg_extractors = [
        ImplicitPathExtractor(),
        SimpleLLMPathExtractor(llm=groq_llm, max_paths_per_chunk=5, num_workers=1),
    ]

    print(f"Indexing page 1/{len(documents)} from {directory}...")
    index = PropertyGraphIndex.from_documents(
        [documents[0]],
        kg_extractors=kg_extractors,
        show_progress=True,
    )

    for i, doc in enumerate(documents[1:], start=2):
        print(f"Sleeping {RATE_LIMIT_SLEEP}s (rate limit)...")
        time.sleep(RATE_LIMIT_SLEEP)
        print(f"Indexing page {i}/{len(documents)} from {directory}...")
        index.insert(doc)

    index.storage_context.persist(persist_dir=persist_dir)
    print(f"Graph index persisted to {persist_dir}")


def main() -> None:
    groq_llm = Groq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
    )

    build_index("civil/", CIVIL_GRAPH_STORE_DIR, groq_llm)
    build_index("labour/", LABOUR_GRAPH_STORE_DIR, groq_llm)


if __name__ == "__main__":
    main()
