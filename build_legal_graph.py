from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import chromadb
import networkx as nx
import pandas as pd


CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "dre_legislacao_em_vigor"

OUT_DIR = Path("legal_csv_output")
OUT_DIR.mkdir(exist_ok=True)

NODES_CSV = OUT_DIR / "legal_nodes.csv"
EDGES_CSV = OUT_DIR / "legal_edges.csv"
CITATIONS_CSV = OUT_DIR / "legal_citations.csv"
METRICS_CSV = OUT_DIR / "legal_graph_metrics.csv"
GRAPH_JSON = OUT_DIR / "legal_graph.json"


RELATION_KEYWORDS = {
    "revokes": [
        "revoga",
        "revogado",
        "revogada",
        "revogam",
        "revogação",
        "revogatória",
    ],
    "amends": [
        "altera",
        "alterado",
        "alterada",
        "alteram",
        "alterações",
        "redação",
        "redacção",
    ],
    "adds": [
        "adita",
        "aditado",
        "aditada",
        "aditamento",
    ],
    "rectifies": [
        "retifica",
        "retificado",
        "retificada",
        "retificação",
        "rectifica",
        "rectificado",
        "rectificada",
        "rectificação",
    ],
    "transposes": [
        "transpõe",
        "transpondo",
        "transposição",
        "diretiva",
        "directiva",
        "ordem jurídica interna",
    ],
    "regulates": [
        "regulamenta",
        "regula",
        "estabelece o regime",
        "estabelece as regras",
        "aprova o regime",
    ],
    "complements": [
        "sem prejuízo",
        "não prejudica",
        "complementar",
        "aplicação de",
    ],
}


LEGAL_DOC_RE = re.compile(
    r"\b(?P<type>"
    r"Decreto-Lei|Decreto\s+Lei|Lei|Portaria|Despacho|Regulamento|"
    r"Diretiva|Directiva|Declaração\s+de\s+Retifica[cç][aã]o|"
    r"Declaração\s+de\s+Rectifica[cç][aã]o|"
    r"Resolução\s+do\s+Conselho\s+de\s+Ministros|Resolução|Aviso|Acórdão"
    r")"
    r"(?:\s+n[.ºo°]*\s*)?"
    r"(?P<number>\d+[/-]?[A-Z]?(?:-?[A-Z])?)"
    r"\s*/\s*"
    r"(?P<year>\d{2,4})"
    r"(?:/(?P<scope>CE|UE|CEE))?",
    flags=re.IGNORECASE,
)

EU_REG_RE = re.compile(
    r"\b(?P<type>Regulamento)\s*\((?P<scope>CE|UE|CEE)\)\s*n[.ºo°]*\s*(?P<number>\d+[/-]?[A-Z]?)\s*/\s*(?P<year>\d{4})",
    flags=re.IGNORECASE,
)


@dataclass
class CitationRow:
    citation_id: str
    source_title: str
    source_theme: str
    source_article: str
    source_pdf_path: str
    target_label: str
    target_type: str
    target_number: str
    target_year: str
    relation_type: str
    citation_text: str
    context: str


@dataclass
class EdgeRow:
    source_id: str
    source_label: str
    target_id: str
    target_label: str
    relation_type: str
    weight: int
    source_theme: str
    source_articles: str
    source_pdf_path: str
    contexts_sample: str


@dataclass
class NodeRow:
    node_id: str
    label: str
    node_type: str
    theme: str
    pdf_path: str


def normalize_spaces(text: str | None) -> str:
    text = text or ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[\u0000-\u001F\u007F-\u009F]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_accents_lower(text: str) -> str:
    text = text.lower()

    replacements = {
        "á": "a",
        "à": "a",
        "â": "a",
        "ã": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
        "º": "",
        "ª": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def slug_id(text: str, max_len: int = 120) -> str:
    normalized = strip_accents_lower(text)
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = normalized.strip("_")

    if normalized:
        return normalized[:max_len]

    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def clean_type(value: str) -> str:
    value = normalize_spaces(value).title()

    replacements = {
        "Decreto Lei": "Decreto-Lei",
        "Directiva": "Diretiva",
        "Declaração De Rectificação": "Declaração de Retificação",
        "Declaração De Retificação": "Declaração de Retificação",
        "Resolução Do Conselho De Ministros": "Resolução do Conselho de Ministros",
    }

    return replacements.get(value, value)


def normalize_year(year: str) -> str:
    year = str(year)

    if len(year) == 2:
        return "20" + year if int(year) <= 30 else "19" + year

    return year


def make_legal_label(legal_type: str, number: str, year: str, scope: str = "") -> str:
    legal_type = clean_type(legal_type)
    year = normalize_year(year)

    if legal_type.lower() == "regulamento" and scope:
        return f"Regulamento ({scope.upper()}) n.º {number}/{year}"

    return f"{legal_type} n.º {number}/{year}"


def infer_relation_type(context: str) -> str:
    context_norm = strip_accents_lower(context)

    for relation, keywords in RELATION_KEYWORDS.items():
        for keyword in keywords:
            if strip_accents_lower(keyword) in context_norm:
                return relation

    return "cites"


def context_window(text: str, start: int, end: int, size: int = 240) -> str:
    return normalize_spaces(text[max(0, start - size): min(len(text), end + size)])


def load_chroma_records() -> list[dict[str, Any]]:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    total = collection.count()
    print(f"Chunks encontrados na ChromaDB: {total}")

    data = collection.get(
        limit=total,
        include=["documents", "metadatas"],
    )

    records = []

    for item_id, document, metadata in zip(
        data.get("ids", []),
        data.get("documents", []),
        data.get("metadatas", []),
    ):
        records.append(
            {
                "id": item_id,
                "document": document or "",
                "metadata": metadata or {},
            }
        )

    return records


def iter_legal_citations(text: str):
    seen_spans = []

    for match in EU_REG_RE.finditer(text):
        seen_spans.append((match.start(), match.end()))
        yield match, match.group("scope") or ""

    for match in LEGAL_DOC_RE.finditer(text):
        duplicate = any(
            abs(match.start() - s) < 5 and abs(match.end() - e) < 15
            for s, e in seen_spans
        )

        if duplicate:
            continue

        yield match, match.groupdict().get("scope") or ""


def extract_citations(records: list[dict[str, Any]]) -> list[CitationRow]:
    rows = []

    for record in records:
        text = normalize_spaces(record.get("document", ""))
        metadata = record.get("metadata", {})

        source_title = normalize_spaces(metadata.get("title", "Sem título"))
        source_theme = normalize_spaces(metadata.get("theme", ""))
        source_article = normalize_spaces(metadata.get("article_id", ""))
        source_pdf_path = normalize_spaces(metadata.get("pdf_path", ""))

        if not text:
            continue

        for match, scope in iter_legal_citations(text):
            legal_type = clean_type(match.group("type"))
            number = match.group("number")
            year = normalize_year(match.group("year"))

            target_label = make_legal_label(legal_type, number, year, scope)
            citation_text = normalize_spaces(match.group(0))
            ctx = context_window(text, match.start(), match.end())
            relation_type = infer_relation_type(ctx)

            if slug_id(target_label) in slug_id(source_title) or slug_id(source_title) in slug_id(target_label):
                continue

            citation_id = hashlib.sha1(
                f"{source_title}|{source_article}|{target_label}|{match.start()}|{ctx[:80]}".encode("utf-8")
            ).hexdigest()[:16]

            rows.append(
                CitationRow(
                    citation_id=citation_id,
                    source_title=source_title,
                    source_theme=source_theme,
                    source_article=source_article,
                    source_pdf_path=source_pdf_path,
                    target_label=target_label,
                    target_type=legal_type,
                    target_number=number,
                    target_year=year,
                    relation_type=relation_type,
                    citation_text=citation_text,
                    context=ctx,
                )
            )

    return rows


def aggregate_edges(citations: list[CitationRow]) -> list[EdgeRow]:
    buckets = defaultdict(list)

    for citation in citations:
        source_id = slug_id(citation.source_title)
        target_id = slug_id(citation.target_label)

        key = (
            source_id,
            citation.source_title,
            target_id,
            citation.target_label,
            citation.relation_type,
        )

        buckets[key].append(citation)

    edges = []

    for (source_id, source_label, target_id, target_label, relation_type), items in buckets.items():
        source_articles = sorted(set(item.source_article for item in items if item.source_article))
        contexts = [item.context for item in items[:3]]

        edges.append(
            EdgeRow(
                source_id=source_id,
                source_label=source_label,
                target_id=target_id,
                target_label=target_label,
                relation_type=relation_type,
                weight=len(items),
                source_theme=items[0].source_theme,
                source_articles=", ".join(source_articles[:10]),
                source_pdf_path=items[0].source_pdf_path,
                contexts_sample=" || ".join(contexts),
            )
        )

    return sorted(edges, key=lambda edge: (-edge.weight, edge.source_label, edge.target_label))


def build_nodes(records: list[dict[str, Any]], edges: list[EdgeRow]) -> list[NodeRow]:
    nodes = {}

    for record in records:
        meta = record.get("metadata", {})
        title = normalize_spaces(meta.get("title", "Sem título"))
        theme = normalize_spaces(meta.get("theme", ""))
        pdf_path = normalize_spaces(meta.get("pdf_path", ""))

        node_id = slug_id(title)

        nodes[node_id] = NodeRow(
            node_id=node_id,
            label=title,
            node_type="source_document",
            theme=theme,
            pdf_path=pdf_path,
        )

    for edge in edges:
        if edge.target_id not in nodes:
            nodes[edge.target_id] = NodeRow(
                node_id=edge.target_id,
                label=edge.target_label,
                node_type="cited_document",
                theme="",
                pdf_path="",
            )

    return list(nodes.values())


def build_networkx_graph(nodes: list[NodeRow], edges: list[EdgeRow]) -> nx.DiGraph:
    graph = nx.DiGraph()

    for node in nodes:
        graph.add_node(
            node.node_id,
            label=node.label,
            node_type=node.node_type,
            theme=node.theme,
            pdf_path=node.pdf_path,
        )

    for edge in edges:
        graph.add_edge(
            edge.source_id,
            edge.target_id,
            relation_type=edge.relation_type,
            weight=edge.weight,
            source_label=edge.source_label,
            target_label=edge.target_label,
            contexts_sample=edge.contexts_sample,
        )

    return graph


def build_metrics(graph: nx.DiGraph) -> pd.DataFrame:
    if graph.number_of_nodes() == 0:
        return pd.DataFrame()

    try:
        pagerank = nx.pagerank(
            graph,
            weight="weight",
            max_iter=100,
            tol=1e-06,
        )
    except Exception as e:
        print(f"[AVISO] PageRank falhou: {e}")
        print("[AVISO] A continuar sem PageRank.")
        pagerank = {node_id: 0 for node_id in graph.nodes}

    rows = []

    for node_id, attrs in graph.nodes(data=True):
        rows.append(
            {
                "node_id": node_id,
                "label": attrs.get("label", ""),
                "node_type": attrs.get("node_type", ""),
                "theme": attrs.get("theme", ""),
                "in_degree": graph.in_degree(node_id),
                "out_degree": graph.out_degree(node_id),
                "weighted_in_degree": sum(
                    data.get("weight", 1)
                    for _, _, data in graph.in_edges(node_id, data=True)
                ),
                "weighted_out_degree": sum(
                    data.get("weight", 1)
                    for _, _, data in graph.out_edges(node_id, data=True)
                ),
                "pagerank": pagerank.get(node_id, 0),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["pagerank", "weighted_in_degree", "weighted_out_degree"],
        ascending=False,
    )


def write_dataclass_csv(path: Path, rows: list[Any]):
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()

        for row in rows:
            writer.writerow(asdict(row))


def save_graph_json(graph: nx.DiGraph):
    data = nx.node_link_data(graph)

    GRAPH_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    records = load_chroma_records()

    citations = extract_citations(records)
    edges = aggregate_edges(citations)
    nodes = build_nodes(records, edges)
    graph = build_networkx_graph(nodes, edges)
    metrics = build_metrics(graph)

    write_dataclass_csv(CITATIONS_CSV, citations)
    write_dataclass_csv(EDGES_CSV, edges)
    write_dataclass_csv(NODES_CSV, nodes)
    metrics.to_csv(METRICS_CSV, index=False, encoding="utf-8-sig")
    save_graph_json(graph)

    print("\nGrafo jurídico construído.")
    print(f"Citações extraídas: {len(citations)}")
    print(f"Nós: {len(nodes)}")
    print(f"Ligações: {len(edges)}")
    print(f"Output: {OUT_DIR}")

    if not metrics.empty:
        print("\nTop 10 nós mais centrais:")
        for _, row in metrics.head(10).iterrows():
            print(
                f"- {row['label']} | PageRank={row['pagerank']:.4f} | "
                f"in={row['weighted_in_degree']} | out={row['weighted_out_degree']}"
            )


if __name__ == "__main__":
    main()