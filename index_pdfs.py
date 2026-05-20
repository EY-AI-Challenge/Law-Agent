import hashlib
import re
import shutil
from pathlib import Path

import chromadb
import fitz
import ollama
from tqdm import tqdm


PDF_DIR = Path("dre_temas_output/pdfs_em_vigor")
CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "dre_legislacao_em_vigor"

EMBED_MODEL = "bge-m3"

MAX_EMBED_CHARS = 1800
CHUNK_OVERLAP = 250

RESET_CHROMA = True


def clean_text(text: str) -> str:
    text = text or ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[\u0000-\u001F\u007F-\u009F]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_pdf(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    pages = []

    for page_number, page in enumerate(doc, start=1):
        text = clean_text(page.get_text("text"))

        if text:
            pages.append(f"\n\n--- PÁGINA {page_number} ---\n\n{text}")

    doc.close()
    return clean_text("\n".join(pages))


def extract_intro_before_first_article(text: str) -> str:
    match = re.search(
        r"\n\s*Artigo\s+\d+[.\wºª\-]*",
        text,
        re.IGNORECASE,
    )

    if not match:
        return ""

    intro = clean_text(text[: match.start()])

    if len(intro) < 200:
        return ""

    return intro


def split_by_articles(text: str) -> list[dict]:
    pattern = re.compile(
        r"(Artigo\s+\d+[.\wºª\-]*.*?)(?=\n\s*Artigo\s+\d+[.\wºª\-]*|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    matches = list(pattern.finditer(text))

    articles = []

    for match in matches:
        article_text = clean_text(match.group(1))

        article_id_match = re.search(
            r"Artigo\s+(\d+[.\wºª\-]*)",
            article_text,
            re.IGNORECASE,
        )

        article_id = article_id_match.group(1) if article_id_match else ""

        if len(article_text) > 150:
            articles.append(
                {
                    "article_id": article_id,
                    "text": article_text,
                }
            )

    return articles


def chunk_text(text: str, max_chars: int = MAX_EMBED_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = clean_text(text)

    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end]

        if end < len(text):
            cut_candidates = [
                chunk.rfind("\n\n"),
                chunk.rfind(". "),
                chunk.rfind("; "),
                chunk.rfind(", "),
            ]

            best_cut = max(cut_candidates)

            if best_cut > max_chars * 0.55:
                end = start + best_cut + 1
                chunk = text[start:end]

        chunk = clean_text(chunk)

        if len(chunk) > 100:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(0, end - overlap)

    return chunks


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_embedding(text: str) -> list[float]:
    text = clean_text(text)

    if len(text) > MAX_EMBED_CHARS:
        text = text[:MAX_EMBED_CHARS]

    response = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=text,
    )

    return response["embedding"]


def make_chunk_id(pdf_hash: str, chunk_index: int, chunk_text_value: str) -> str:
    raw = f"{pdf_hash}:{chunk_index}:{chunk_text_value[:120]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_payloads_from_pdf_text(text: str) -> list[dict]:
    payloads = []

    intro = extract_intro_before_first_article(text)

    if intro:
        for i, intro_chunk in enumerate(chunk_text(intro)):
            payloads.append(
                {
                    "text": intro_chunk,
                    "article_id": "",
                    "chunk_type": "intro",
                    "subchunk_index": i,
                }
            )

    articles = split_by_articles(text)

    if articles:
        for article in articles:
            for sub_i, article_chunk in enumerate(chunk_text(article["text"])):
                payloads.append(
                    {
                        "text": article_chunk,
                        "article_id": article["article_id"],
                        "chunk_type": "article",
                        "subchunk_index": sub_i,
                    }
                )
    else:
        for i, chunk in enumerate(chunk_text(text)):
            payloads.append(
                {
                    "text": chunk,
                    "article_id": "",
                    "chunk_type": "chunk",
                    "subchunk_index": i,
                }
            )

    return payloads


def index_pdf(collection, pdf_path: Path) -> int:
    theme = pdf_path.parent.name
    title = pdf_path.stem
    pdf_hash = file_hash(pdf_path)

    text = extract_text_from_pdf(pdf_path)

    if not text:
        print(f"[AVISO] Sem texto extraído: {pdf_path}")
        return 0

    chunks_payload = build_payloads_from_pdf_text(text)

    inserted = 0

    for i, payload in enumerate(chunks_payload):
        chunk = payload["text"]
        chunk_id = make_chunk_id(pdf_hash, i, chunk)
        embedding = get_embedding(chunk)

        metadata = {
            "theme": theme,
            "title": title,
            "pdf_path": str(pdf_path),
            "chunk_index": i,
            "subchunk_index": payload.get("subchunk_index", 0),
            "chunk_type": payload["chunk_type"],
            "article_id": payload["article_id"],
            "source_hash": pdf_hash,
        }

        collection.upsert(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[metadata],
        )

        inserted += 1

    return inserted


def reset_chroma_if_needed():
    if RESET_CHROMA and CHROMA_DIR.exists():
        print(f"A apagar base vetorial antiga: {CHROMA_DIR}")
        shutil.rmtree(CHROMA_DIR)


def main():
    if not PDF_DIR.exists():
        raise FileNotFoundError(
            f"Não encontrei a pasta {PDF_DIR}. Primeiro corre: py main.py"
        )

    pdfs = sorted(PDF_DIR.rglob("*.pdf"))

    print(f"PDFs encontrados: {len(pdfs)}")

    if not pdfs:
        print("Não há PDFs para indexar.")
        return

    reset_chroma_if_needed()

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Legislação portuguesa em vigor do DRE"},
    )

    total_chunks = 0
    failed = []

    for pdf_path in tqdm(pdfs, desc="A indexar PDFs"):
        try:
            inserted = index_pdf(collection, pdf_path)
            total_chunks += inserted
        except Exception as e:
            print(f"[ERRO] Falhou ao indexar {pdf_path}: {e}")
            failed.append(
                {
                    "pdf": str(pdf_path),
                    "error": str(e),
                }
            )

    print("\nIndexação concluída.")
    print(f"PDFs encontrados: {len(pdfs)}")
    print(f"PDFs com erro: {len(failed)}")
    print(f"Chunks/artigos indexados: {total_chunks}")
    print(f"Base vetorial: {CHROMA_DIR}")
    print(f"Coleção: {COLLECTION_NAME}")

    if failed:
        print("\nPDFs que falharam:")
        for item in failed:
            print(f"- {item['pdf']}")
            print(f"  {item['error']}")


if __name__ == "__main__":
    main()