from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import chromadb
import networkx as nx
import ollama
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from networkx.algorithms.community import greedy_modularity_communities


# ============================================================
# Configuração
# ============================================================

CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "dre_legislacao_em_vigor"

GRAPH_DIR = Path("legal_csv_output")
EDGES_CSV = GRAPH_DIR / "legal_edges.csv"
NODES_CSV = GRAPH_DIR / "legal_nodes.csv"
METRICS_CSV = GRAPH_DIR / "legal_graph_metrics.csv"

EMBED_MODEL = "bge-m3"
LLM_MODEL = "qwen2.5:14b"


RELATION_LABELS = {
    "cites": "cita",
    "revokes": "revoga / é revogado por",
    "amends": "altera / é alterado por",
    "adds": "adita / é aditado por",
    "rectifies": "retifica / é retificado por",
    "transposes": "transpõe / implementa",
    "regulates": "regulamenta / estabelece regime",
    "complements": "complementa / preserva regime",
}


SYSTEM_PROMPT = """
És um assistente jurídico especializado em legislação portuguesa.

Regras obrigatórias:
1. Responde apenas com base no CONTEXTO TEXTUAL e no GRAFO DE RELAÇÕES LEGAIS fornecidos.
2. Usa o CONTEXTO TEXTUAL para explicar o conteúdo dos diplomas.
3. Usa o GRAFO DE RELAÇÕES LEGAIS para explicar citações, dependências, alterações, revogações, correlações, clusters e ligações entre diplomas.
4. Se a informação não existir no contexto, diz claramente:
   "Não encontrei informação suficiente nos documentos indexados."
5. Não inventes artigos, diplomas, datas, prazos ou interpretações.
6. Sempre que possível, indica os diplomas/fontes usados.
7. Se a pergunta mencionar um ou mais diplomas específicos, dá prioridade a esses diplomas.
8. Se a pergunta pedir correlação, relação, dependência, citações ou ligações, deves analisar também os diplomas relacionados no grafo.
9. Distingue claramente "citações diretas" de outras relações como alteração, revogação, aditamento, regulamentação ou transposição.
10. Se forem pedidos clusters, explica que são agrupamentos estruturais do grafo, não categorias jurídicas oficiais.
11. Se a pergunta for educativa, responde como tutor para estudantes, com linguagem clara e exemplos simples.
12. Não apresentes a resposta como aconselhamento jurídico definitivo.
13. Responde em português de Portugal, de forma clara e estruturada.
"""


# ============================================================
# Utilitários
# ============================================================

def safe_str(value) -> str:
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def clean_text(text: str) -> str:
    text = text or ""
    text = re.sub(r"[\u0000-\u001F\u007F-\u009F]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_for_match(text: str) -> str:
    text = text or ""
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
        "°": "",
        "n.º": "n",
        "n.o": "n",
        "nº": "n",
        "n.": "n",
        "decreto lei": "decretolei",
        "decreto-lei": "decretolei",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def clean_label_for_display(label: str) -> str:
    label = safe_str(label)
    label = label.replace("_", " ")
    label = re.sub(r"\s+", " ", label)
    label = label.replace("n. º", "n.º")
    label = label.replace("n .º", "n.º")
    label = label.replace("nº", "n.º")
    label = re.sub(r"\s*-\s*Diário da República.*$", "", label, flags=re.IGNORECASE)
    return label.strip()


def shorten(text: str, max_len: int = 260) -> str:
    text = clean_text(text)

    if len(text) <= max_len:
        return text

    return text[:max_len].rstrip() + "..."


def extract_json_from_text(text: str):
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"```json\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    return None


# ============================================================
# Deteção de diplomas e intenção
# ============================================================

def make_diploma_dict(diploma_type: str, number: str, year: str) -> dict:
    if diploma_type.upper() == "DL":
        diploma_type = "Decreto-Lei"

    if diploma_type.lower() in ["decreto", "decreto lei", "decreto-lei"]:
        diploma_type = "Decreto-Lei"

    raw = f"{diploma_type} n.º {number}/{year}"

    return {
        "raw": raw,
        "type": diploma_type,
        "number": number,
        "year": year,
        "compact_number_year": f"{number}{year}".lower(),
        "normalized": normalize_for_match(raw),
    }


def extract_all_diplomas_from_question(question: str) -> list[dict]:
    patterns = [
        r"(Decreto[-\s]?Lei|Decreto|DL)\s*(?:n\.?\s*[ºo°]?)?\s*([\d]+[A-Z]?)\s*/\s*(\d{4})",
        r"(Lei)\s*(?:n\.?\s*[ºo°]?)?\s*([\d]+[A-Z]?)\s*/\s*(\d{4})",
        r"(Portaria)\s*(?:n\.?\s*[ºo°]?)?\s*([\d]+[A-Z]?)\s*/\s*(\d{4})",
        r"(Despacho)\s*(?:n\.?\s*[ºo°]?)?\s*([\d]+[A-Z]?)\s*/\s*(\d{4})",
        r"(Regulamento)\s*(?:n\.?\s*[ºo°]?)?\s*([\d]+[A-Z]?)\s*/\s*(\d{4})",
        r"(Aviso)\s*(?:n\.?\s*[ºo°]?)?\s*([\d]+[A-Z]?)\s*/\s*(\d{4})",
        r"(Resolução do Conselho de Ministros)\s*(?:n\.?\s*[ºo°]?)?\s*([\d]+[A-Z]?)\s*/\s*(\d{4})",
        r"(Resolução)\s*(?:n\.?\s*[ºo°]?)?\s*([\d]+[A-Z]?)\s*/\s*(\d{4})",
        r"(Acórdão)\s*(?:n\.?\s*[ºo°]?)?\s*([\d]+[A-Z]?)\s*/\s*(\d{4})",
    ]

    diplomas = []
    seen = set()

    for pattern in patterns:
        for match in re.finditer(pattern, question, re.IGNORECASE):
            diploma = make_diploma_dict(
                match.group(1),
                match.group(2),
                match.group(3),
            )

            key = diploma["compact_number_year"]

            if key not in seen:
                seen.add(key)
                diplomas.append(diploma)

    return diplomas


def extract_specific_diploma_query(question: str) -> dict | None:
    diplomas = extract_all_diplomas_from_question(question)
    return diplomas[0] if diplomas else None


def is_graph_question(question: str) -> bool:
    q = normalize_for_match(question)

    graph_terms = [
        "citado",
        "citados",
        "cita",
        "citam",
        "referencia",
        "referencias",
        "referenciado",
        "referenciados",
        "relacionado",
        "relacionados",
        "relacoes",
        "relacao",
        "correlacao",
        "correlacoes",
        "dependencias",
        "dependencia",
        "revoga",
        "revogados",
        "revogacao",
        "altera",
        "alterados",
        "alteracao",
        "adita",
        "aditamento",
        "retifica",
        "retificacao",
        "transpoe",
        "transposicao",
        "grafo",
        "rede",
        "ligacoes",
        "ligacao",
        "conexao",
        "conexoes",
        "cluster",
        "clusters",
        "comunidade",
        "comunidades",
        "grupo",
        "grupos",
    ]

    return any(term in q for term in graph_terms)


def is_cluster_question(question: str) -> bool:
    q = normalize_for_match(question)

    return any(
        term in q
        for term in [
            "cluster",
            "clusters",
            "comunidade",
            "comunidades",
            "grupo",
            "grupos",
            "agrupamento",
            "agrupamentos",
        ]
    )


def is_learning_question(question: str) -> bool:
    q = normalize_for_match(question)

    learning_terms = [
        "aprender",
        "estudar",
        "estudante",
        "estudantes",
        "explica",
        "explicame",
        "explicacao",
        "resumo",
        "resumir",
        "quiz",
        "quizz",
        "perguntas",
        "teste",
        "exercicio",
        "exercicios",
        "conceitos",
        "conceitoschave",
        "flashcards",
        "ensina",
        "tutor",
        "aula",
        "simplifica",
        "linguagemsimples",
    ]

    return any(term in q for term in learning_terms)


def wants_quiz(question: str) -> bool:
    q = normalize_for_match(question)

    return any(
        term in q
        for term in [
            "quiz",
            "quizz",
            "perguntas",
            "teste",
            "exercicio",
            "exercicios",
            "avaliacao",
        ]
    )


def desired_relation_types_from_question(question: str) -> list[str] | None:
    q = normalize_for_match(question)

    if any(term in q for term in ["citados", "citado", "cita", "citam", "referencia", "referencias"]):
        return ["cites"]

    if any(term in q for term in ["revoga", "revogacao", "revogados", "revogado"]):
        return ["revokes"]

    if any(term in q for term in ["altera", "alteracao", "alterados", "alterado"]):
        return ["amends"]

    if any(term in q for term in ["adita", "aditamento", "aditados", "aditado"]):
        return ["adds"]

    if any(term in q for term in ["retifica", "retificacao", "retificado"]):
        return ["rectifies"]

    if any(term in q for term in ["transpoe", "transposicao", "diretiva", "directiva"]):
        return ["transposes"]

    if any(term in q for term in ["regulamenta", "regula", "regime", "estabelece"]):
        return ["regulates"]

    return None


def article_priority(article_id: str, chunk_index: int) -> int:
    article_id = article_id or ""

    if article_id == "":
        return 0

    normalized = article_id.replace("º", "").replace(".", "").strip()
    match = re.match(r"(\d+)", normalized)

    if not match:
        return 1000 + int(chunk_index or 0)

    number = int(match.group(1))

    if number == 1:
        return 1

    if number == 2:
        return 2

    if number == 3:
        return 3

    return 100 + number


# ============================================================
# ChromaDB
# ============================================================

def get_embedding(text: str) -> list[float]:
    response = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=text,
    )

    return response["embedding"]


@st.cache_resource
def load_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME)


def retrieve_exact_diploma_chunks(diploma: dict, n_results: int = 6) -> list[dict[str, Any]]:
    collection = load_collection()
    total = collection.count()

    data = collection.get(
        limit=total,
        include=["documents", "metadatas"],
    )

    documents = data.get("documents", [])
    metadatas = data.get("metadatas", [])

    exact = []

    for doc, meta in zip(documents, metadatas):
        meta = meta or {}

        title = meta.get("title", "")
        pdf_path = meta.get("pdf_path", "")
        haystack = normalize_for_match(f"{title} {pdf_path}")

        if diploma["compact_number_year"] not in haystack:
            continue

        exact.append(
            {
                "text": clean_text(doc),
                "metadata": meta,
                "distance": 0,
                "matches_specific_diploma": True,
                "source_reason": "diploma_exato",
            }
        )

    exact = sorted(
        exact,
        key=lambda item: (
            article_priority(
                str(item["metadata"].get("article_id", "")),
                int(item["metadata"].get("chunk_index", 0)),
            ),
            int(item["metadata"].get("subchunk_index", 0)),
        ),
    )

    return exact[:n_results]


def retrieve_chunks_by_title_or_label(label: str, n_results: int = 3) -> list[dict[str, Any]]:
    collection = load_collection()
    total = collection.count()

    data = collection.get(
        limit=total,
        include=["documents", "metadatas"],
    )

    documents = data.get("documents", [])
    metadatas = data.get("metadatas", [])

    target_norm = normalize_for_match(label)
    results = []

    num_year_match = re.search(r"(\d+[A-Z]?)\s*/\s*(\d{4})", label, re.IGNORECASE)
    compact = ""

    if num_year_match:
        compact = f"{num_year_match.group(1)}{num_year_match.group(2)}".lower()

    for doc, meta in zip(documents, metadatas):
        meta = meta or {}

        title = meta.get("title", "")
        pdf_path = meta.get("pdf_path", "")
        haystack = normalize_for_match(f"{title} {pdf_path}")

        matched = False

        if compact and compact in haystack:
            matched = True
        elif target_norm and target_norm in haystack:
            matched = True

        if not matched:
            continue

        results.append(
            {
                "text": clean_text(doc),
                "metadata": meta,
                "distance": 0,
                "matches_specific_diploma": True,
                "source_reason": "diploma_relacionado",
            }
        )

    results = sorted(
        results,
        key=lambda item: (
            article_priority(
                str(item["metadata"].get("article_id", "")),
                int(item["metadata"].get("chunk_index", 0)),
            ),
            int(item["metadata"].get("subchunk_index", 0)),
        ),
    )

    return results[:n_results]


def retrieve_vector_context(question: str, n_results: int = 6) -> list[dict[str, Any]]:
    collection = load_collection()
    query_embedding = get_embedding(question)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    retrieved = []

    for doc, meta, distance in zip(documents, metadatas, distances):
        retrieved.append(
            {
                "text": clean_text(doc),
                "metadata": meta or {},
                "distance": distance,
                "matches_specific_diploma": False,
                "source_reason": "pesquisa_vetorial",
            }
        )

    return retrieved


def deduplicate_sources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    unique = []

    for item in items:
        meta = item.get("metadata", {})

        key = (
            meta.get("title", ""),
            meta.get("article_id", ""),
            meta.get("chunk_index", ""),
            meta.get("subchunk_index", ""),
            item.get("text", "")[:80],
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


# ============================================================
# Grafo
# ============================================================

@st.cache_data(show_spinner=False)
def load_graph_data():
    if not EDGES_CSV.exists() or not NODES_CSV.exists() or not METRICS_CSV.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), nx.DiGraph()

    edges_df = pd.read_csv(EDGES_CSV)
    nodes_df = pd.read_csv(NODES_CSV)
    metrics_df = pd.read_csv(METRICS_CSV)

    edges_df = edges_df.fillna("")
    nodes_df = nodes_df.fillna("")
    metrics_df = metrics_df.fillna("")

    graph = nx.DiGraph()

    for _, row in nodes_df.iterrows():
        graph.add_node(
            safe_str(row.get("node_id", "")),
            label=safe_str(row.get("label", "")),
            node_type=safe_str(row.get("node_type", "")),
            theme=safe_str(row.get("theme", "")),
            pdf_path=safe_str(row.get("pdf_path", "")),
        )

    for _, row in edges_df.iterrows():
        source_id = safe_str(row.get("source_id", ""))
        target_id = safe_str(row.get("target_id", ""))
        source_label = safe_str(row.get("source_label", ""))
        target_label = safe_str(row.get("target_label", ""))

        if not source_id or not target_id:
            continue

        if source_id == target_id:
            continue

        if normalize_for_match(source_label) == normalize_for_match(target_label):
            continue

        graph.add_edge(
            source_id,
            target_id,
            weight=int(float(row.get("weight", 1) or 1)),
            relation_type=safe_str(row.get("relation_type", "cites")),
            source_label=source_label,
            target_label=target_label,
            contexts_sample=safe_str(row.get("contexts_sample", "")),
        )

    return edges_df, nodes_df, metrics_df, graph


def compute_graph_clusters(graph: nx.DiGraph) -> tuple[dict[str, int], pd.DataFrame]:
    if graph.number_of_nodes() == 0:
        return {}, pd.DataFrame()

    undirected = graph.to_undirected()

    communities = list(
        greedy_modularity_communities(
            undirected,
            weight="weight",
        )
    )

    node_to_cluster = {}
    rows = []

    for cluster_id, community in enumerate(communities, start=1):
        subgraph = graph.subgraph(community).copy()

        themes = []
        relation_types = []

        for node in community:
            theme = safe_str(graph.nodes[node].get("theme", ""))

            if theme:
                themes.append(theme)

        for _u, _v, data in subgraph.edges(data=True):
            relation_type = safe_str(data.get("relation_type", "cites"))

            if relation_type:
                relation_types.append(RELATION_LABELS.get(relation_type, relation_type))

        top_nodes = sorted(
            subgraph.degree(weight="weight"),
            key=lambda item: item[1],
            reverse=True,
        )[:8]

        top_labels = []

        for node, _degree in top_nodes:
            label = clean_label_for_display(graph.nodes[node].get("label", node))

            if label:
                top_labels.append(label)

        for node in community:
            node_to_cluster[node] = cluster_id

        rows.append(
            {
                "cluster_id": cluster_id,
                "num_nodes": len(community),
                "num_edges": subgraph.number_of_edges(),
                "top_nodes": " | ".join(top_labels),
                "themes_sample": " | ".join(sorted(set(themes))[:8]),
                "relation_types": " | ".join(sorted(set(relation_types))[:8]),
            }
        )

    clusters_df = pd.DataFrame(rows)

    if clusters_df.empty:
        return node_to_cluster, clusters_df

    clusters_df = clusters_df.sort_values(
        ["num_nodes", "num_edges"],
        ascending=False,
    )

    return node_to_cluster, clusters_df


def find_graph_node_for_diploma(graph: nx.DiGraph, diploma: dict | None):
    if graph is None or diploma is None:
        return None

    compact = diploma["compact_number_year"]

    for node_id, attrs in graph.nodes(data=True):
        label = attrs.get("label", "")
        haystack = normalize_for_match(f"{node_id} {label}")

        if compact in haystack:
            return node_id, attrs

    return None


def build_contextual_subgraph(graph: nx.DiGraph, diploma: dict | None, depth: int = 1) -> nx.DiGraph:
    found = find_graph_node_for_diploma(graph, diploma)

    if not found:
        return nx.DiGraph()

    node_id, _attrs = found

    nodes = {node_id}
    frontier = {node_id}

    for _ in range(depth):
        new_frontier = set()

        for node in frontier:
            neighbors = set(graph.successors(node)) | set(graph.predecessors(node))
            new_frontier.update(neighbors)

        nodes.update(new_frontier)
        frontier = new_frontier

    return graph.subgraph(nodes).copy()


def build_multi_diploma_subgraph(
    graph: nx.DiGraph,
    diplomas: list[dict],
    include_neighbors: bool = True,
    depth: int = 1,
) -> nx.DiGraph:
    if not diplomas:
        return nx.DiGraph()

    matched_nodes = []

    for diploma in diplomas:
        found = find_graph_node_for_diploma(graph, diploma)

        if found:
            node_id, _attrs = found
            matched_nodes.append(node_id)

    if not matched_nodes:
        return nx.DiGraph()

    nodes = set(matched_nodes)
    undirected = graph.to_undirected()

    for i in range(len(matched_nodes)):
        for j in range(i + 1, len(matched_nodes)):
            source = matched_nodes[i]
            target = matched_nodes[j]

            if nx.has_path(undirected, source, target):
                try:
                    path = nx.shortest_path(undirected, source, target)
                    nodes.update(path)
                except Exception:
                    pass

    if include_neighbors:
        frontier = set(nodes)

        for _ in range(depth):
            new_frontier = set()

            for node in frontier:
                neighbors = set(graph.successors(node)) | set(graph.predecessors(node))
                new_frontier.update(neighbors)

            nodes.update(new_frontier)
            frontier = new_frontier

    return graph.subgraph(nodes).copy()


def get_edges_for_diploma(
    edges_df: pd.DataFrame,
    diploma: dict | None,
    question: str = "",
    allow_fallback: bool = True,
) -> tuple[pd.DataFrame, bool]:
    if diploma is None or edges_df.empty:
        return pd.DataFrame(), False

    compact = diploma["compact_number_year"]

    def row_matches(value: str) -> bool:
        return compact in normalize_for_match(str(value))

    mask_source = edges_df["source_label"].apply(row_matches)
    mask_target = edges_df["target_label"].apply(row_matches)

    matched_all = edges_df[mask_source | mask_target].copy()

    if matched_all.empty:
        return matched_all, False

    matched_all["direction"] = matched_all.apply(
        lambda row: "outgoing" if row_matches(row["source_label"]) else "incoming",
        axis=1,
    )

    desired_relations = desired_relation_types_from_question(question)

    if desired_relations is None:
        return matched_all.sort_values(["direction", "weight"], ascending=[False, False]), False

    matched_filtered = matched_all[matched_all["relation_type"].isin(desired_relations)].copy()

    if not matched_filtered.empty:
        return matched_filtered.sort_values(["direction", "weight"], ascending=[False, False]), False

    if allow_fallback:
        return matched_all.sort_values(["direction", "weight"], ascending=[False, False]), True

    return matched_filtered, False


def get_edges_between_many_diplomas(edges_df: pd.DataFrame, diplomas: list[dict]) -> pd.DataFrame:
    if edges_df.empty or len(diplomas) < 2:
        return pd.DataFrame()

    def which_diploma(value: str) -> str:
        normalized = normalize_for_match(str(value))

        for diploma in diplomas:
            if diploma["compact_number_year"] in normalized:
                return diploma["raw"]

        return ""

    result = edges_df.copy()
    result["source_match"] = result["source_label"].apply(which_diploma)
    result["target_match"] = result["target_label"].apply(which_diploma)

    result = result[
        (result["source_match"] != "")
        & (result["target_match"] != "")
        & (result["source_match"] != result["target_match"])
    ].copy()

    if result.empty:
        return result

    result["pair"] = result.apply(
        lambda row: f"{row['source_match']} → {row['target_match']}",
        axis=1,
    )

    return result.sort_values(["pair", "relation_type", "weight"], ascending=[True, True, False])


def build_graph_context_from_edges(
    edges_for_diploma: pd.DataFrame,
    diploma: dict | None,
    fallback_used: bool = False,
) -> tuple[str, list[str]]:
    if diploma is None or edges_for_diploma.empty:
        return "", []

    lines = []
    related_labels = []

    lines.append(f"Diploma principal: {diploma['raw']}")

    if fallback_used:
        lines.append(
            "\nNota: não foram encontradas relações exatamente do tipo pedido. "
            "São apresentadas outras relações legais encontradas no grafo."
        )

    outgoing = edges_for_diploma[edges_for_diploma["direction"] == "outgoing"]
    incoming = edges_for_diploma[edges_for_diploma["direction"] == "incoming"]

    if not outgoing.empty:
        lines.append("\nRelações saídas do diploma principal:")

        for relation_type, group in outgoing.groupby("relation_type"):
            relation_label = RELATION_LABELS.get(relation_type, relation_type)
            lines.append(f"\nTipo de relação: {relation_label}")

            for _, row in group.iterrows():
                target = row.get("target_label", "")
                weight = row.get("weight", 1)
                context = row.get("contexts_sample", "")

                related_labels.append(target)

                lines.append(
                    f"- {clean_label_for_display(target)} | peso: {weight} | contexto: {shorten(str(context), 450)}"
                )

    if not incoming.empty:
        lines.append("\nRelações recebidas pelo diploma principal:")

        for relation_type, group in incoming.groupby("relation_type"):
            relation_label = RELATION_LABELS.get(relation_type, relation_type)
            lines.append(f"\nTipo de relação: {relation_label}")

            for _, row in group.iterrows():
                source = row.get("source_label", "")
                weight = row.get("weight", 1)
                context = row.get("contexts_sample", "")

                related_labels.append(source)

                lines.append(
                    f"- {clean_label_for_display(source)} | peso: {weight} | contexto: {shorten(str(context), 450)}"
                )

    seen = set()
    unique_related = []

    for label in related_labels:
        if label and label not in seen:
            seen.add(label)
            unique_related.append(label)

    return "\n".join(lines), unique_related


def build_many_diplomas_graph_context(edges_between: pd.DataFrame, diplomas: list[dict]) -> tuple[str, list[str]]:
    if len(diplomas) < 2:
        return "", []

    names = ", ".join(d["raw"] for d in diplomas)

    if edges_between.empty:
        return f"Não foram encontradas relações diretas no grafo entre os diplomas indicados: {names}.", []

    lines = []
    related_labels = []

    lines.append(f"Diplomas analisados: {names}")
    lines.append("\nRelações diretas encontradas entre os diplomas indicados:")

    for _, row in edges_between.iterrows():
        relation = row.get("relation_type", "cites")
        relation_label = RELATION_LABELS.get(relation, relation)
        source = row.get("source_label", "")
        target = row.get("target_label", "")
        weight = row.get("weight", 1)
        context = row.get("contexts_sample", "")

        related_labels.append(source)
        related_labels.append(target)

        lines.append("")
        lines.append(f"- {clean_label_for_display(source)} → {clean_label_for_display(target)}")
        lines.append(f"  Relação: {relation_label}")
        lines.append(f"  Peso: {weight}")
        lines.append(f"  Contexto: {shorten(str(context), 500)}")

    return "\n".join(lines), related_labels


def build_cluster_context(
    graph: nx.DiGraph,
    clusters_df: pd.DataFrame,
    diplomas: list[dict],
    node_to_cluster: dict[str, int],
) -> str:
    if clusters_df.empty:
        return "Não foi possível calcular clusters no grafo."

    if not diplomas:
        lines = []
        lines.append("Clusters principais encontrados no grafo jurídico:")

        for _, row in clusters_df.head(8).iterrows():
            lines.append("")
            lines.append(f"- Cluster {row['cluster_id']}")
            lines.append(f"  Nós: {row['num_nodes']} | Ligações: {row['num_edges']}")
            lines.append(f"  Nós centrais/exemplos: {row['top_nodes']}")
            lines.append(f"  Tipos de relação: {row['relation_types']}")

        return "\n".join(lines)

    lines = []

    for diploma in diplomas:
        found = find_graph_node_for_diploma(graph, diploma)

        if not found:
            lines.append(f"- {diploma['raw']}: não encontrado no grafo.")
            continue

        node_id, attrs = found
        cluster_id = node_to_cluster.get(node_id)

        if not cluster_id:
            lines.append(f"- {diploma['raw']}: encontrado, mas sem cluster associado.")
            continue

        cluster_row = clusters_df[clusters_df["cluster_id"] == cluster_id]

        if cluster_row.empty:
            continue

        row = cluster_row.iloc[0]

        lines.append("")
        lines.append(f"{diploma['raw']} pertence ao Cluster {cluster_id}.")
        lines.append(f"Nós no cluster: {row['num_nodes']} | Ligações: {row['num_edges']}")
        lines.append(f"Exemplos/nós centrais: {row['top_nodes']}")
        lines.append(f"Tipos de relação no cluster: {row['relation_types']}")

    return "\n".join(lines)


def retrieve_context(
    question: str,
    graph: nx.DiGraph,
    edges_df: pd.DataFrame,
    clusters_df: pd.DataFrame,
    node_to_cluster: dict[str, int],
    n_results: int = 6,
) -> tuple[list[dict[str, Any]], str, pd.DataFrame, bool]:
    diplomas = extract_all_diplomas_from_question(question)
    graph_question = is_graph_question(question)
    cluster_question = is_cluster_question(question)
    learning_question = is_learning_question(question)

    retrieved: list[dict[str, Any]] = []
    graph_context = ""
    edges_result = pd.DataFrame()
    fallback_used = False

    if diplomas:
        if learning_question:
            for diploma in diplomas[:2]:
                retrieved.extend(retrieve_exact_diploma_chunks(diploma, n_results=max(n_results, 12)))
        else:
            for diploma in diplomas[:5]:
                retrieved.extend(retrieve_exact_diploma_chunks(diploma, n_results=4))

    if cluster_question:
        graph_context = build_cluster_context(
            graph,
            clusters_df,
            diplomas,
            node_to_cluster,
        )

    elif len(diplomas) >= 2:
        edges_result = get_edges_between_many_diplomas(edges_df, diplomas)
        graph_context, related_labels = build_many_diplomas_graph_context(edges_result, diplomas)

        for label in related_labels[:10]:
            retrieved.extend(retrieve_chunks_by_title_or_label(label, n_results=2))

    elif len(diplomas) == 1 and graph_question:
        diploma = diplomas[0]

        edges_result, fallback_used = get_edges_for_diploma(
            edges_df,
            diploma,
            question=question,
            allow_fallback=True,
        )

        graph_context, related_labels = build_graph_context_from_edges(
            edges_result,
            diploma,
            fallback_used=fallback_used,
        )

        for label in related_labels[:8]:
            retrieved.extend(retrieve_chunks_by_title_or_label(label, n_results=2))

    if not retrieved:
        retrieved.extend(retrieve_vector_context(question, n_results=n_results))

    retrieved = deduplicate_sources(retrieved)

    max_total_sources = max(n_results, 18 if learning_question else 14 if graph_question else n_results)
    retrieved = retrieved[:max_total_sources]

    return retrieved, graph_context, edges_result, fallback_used


# ============================================================
# Contexto e LLM
# ============================================================

def build_text_context(retrieved: list[dict[str, Any]]) -> str:
    blocks = []

    for i, item in enumerate(retrieved, start=1):
        meta = item["metadata"]

        block = f"""
[FONTE {i}]
Motivo da fonte: {item.get("source_reason", "")}
Tema: {meta.get("theme", "")}
Diploma: {meta.get("title", "")}
Artigo: {meta.get("article_id", "")}
Tipo de excerto: {meta.get("chunk_type", "")}
Chunk: {meta.get("chunk_index", "")}
Subchunk: {meta.get("subchunk_index", "")}
PDF local: {meta.get("pdf_path", "")}

TEXTO:
{item["text"]}
"""
        blocks.append(block)

    return "\n\n".join(blocks)


def ask_llm(question: str, text_context: str, graph_context: str, fallback_used: bool = False) -> str:
    graph_mode = is_graph_question(question)
    cluster_mode = is_cluster_question(question)
    learning_mode = is_learning_question(question)
    quiz_mode = wants_quiz(question)
    desired = desired_relation_types_from_question(question)

    desired_text = ""

    if desired:
        readable = ", ".join(RELATION_LABELS.get(item, item) for item in desired)
        desired_text = f"O utilizador pediu principalmente relações do tipo: {readable}."

    fallback_text = ""

    if fallback_used:
        fallback_text = """
Não foram encontradas relações exatamente do tipo pedido.
Explica isso claramente e depois apresenta as outras relações encontradas, sem as confundir com citações diretas.
"""

    if learning_mode:
        if quiz_mode:
            mode_instruction = """
A pergunta é educativa e o utilizador pediu um quiz/teste/exercícios.
Age como tutor jurídico para estudantes.

Estrutura obrigatória:
1. Título da aula.
2. Resumo simples do diploma.
3. Objetivo principal da lei.
4. Conceitos-chave.
5. Mini-quiz com perguntas de treino.
6. Não inventes temas fora do contexto.
7. Nota: isto não substitui aconselhamento jurídico.
"""
        else:
            mode_instruction = """
A pergunta é educativa.
Age como tutor jurídico para estudantes.

Estrutura recomendada:
1. Resumo curto.
2. Explicação em linguagem simples.
3. Objetivo principal do diploma.
4. Conceitos-chave.
5. Pontos importantes a memorizar.
6. Exemplo prático simples, se o contexto permitir.
7. Nota de cautela: isto não substitui aconselhamento jurídico.
"""
    elif cluster_mode:
        mode_instruction = """
A pergunta é sobre clusters/comunidades no grafo legal.
Explica que os clusters são agrupamentos automáticos baseados nas ligações entre diplomas.
Não afirmes que são categorias jurídicas oficiais.
Identifica os diplomas ou temas centrais do cluster quando possível.
"""
    elif graph_mode:
        mode_instruction = f"""
A pergunta é sobre correlação, relação, dependência, citação, alteração, revogação ou ligação entre diplomas.
Deves dar prioridade ao GRAFO DE RELAÇÕES LEGAIS.
{desired_text}
{fallback_text}
Usa também o CONTEXTO TEXTUAL dos diplomas relacionados para justificar a resposta.
Indica claramente as fontes consultadas e os diplomas envolvidos.
Distingue citações diretas de outras relações legais.
Se existirem vários diplomas na pergunta, foca-te nas relações entre esses diplomas.
Se o grafo não tiver ligações suficientes, diz isso claramente.
"""
    else:
        mode_instruction = """
A pergunta é principalmente sobre o conteúdo de um diploma.
Dá prioridade ao CONTEXTO TEXTUAL.
Usa o grafo apenas se ajudar a explicar relações com outros diplomas.
"""

    prompt = f"""
{SYSTEM_PROMPT}

MODO DE RESPOSTA:
{mode_instruction}

CONTEXTO TEXTUAL:
{text_context}

GRAFO DE RELAÇÕES LEGAIS:
{graph_context}

PERGUNTA DO UTILIZADOR:
{question}

RESPOSTA:
"""

    response = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.12 if learning_mode else 0.03, "top_p": 0.9},
    )

    return response["message"]["content"]


# ============================================================
# Quiz interativo
# ============================================================

def validate_quiz_json(quiz: dict, expected_num_questions: int | None = None) -> bool:
    if not isinstance(quiz, dict):
        return False

    if "title" not in quiz:
        return False

    if "questions" not in quiz:
        return False

    if not isinstance(quiz["questions"], list):
        return False

    if len(quiz["questions"]) == 0:
        return False

    if expected_num_questions is not None and len(quiz["questions"]) != expected_num_questions:
        return False

    for q in quiz["questions"]:
        if not isinstance(q, dict):
            return False

        if q.get("type") not in ["multiple_choice", "short_answer"]:
            return False

        if not q.get("question"):
            return False

        if "expected_answer" not in q:
            return False

        if "explanation" not in q:
            return False

        if q.get("type") == "multiple_choice":
            options = q.get("options")

            if not isinstance(options, list):
                return False

            if len(options) < 2:
                return False

            correct_option = q.get("correct_option")

            if not isinstance(correct_option, int):
                return False

            if correct_option < 0 or correct_option >= len(options):
                return False

        if q.get("type") == "short_answer":
            if q.get("options") not in [[], None]:
                return False

    return True


def fallback_quiz(law_label: str, num_questions: int = 6) -> dict:
    base_questions = [
        {
            "type": "multiple_choice",
            "question": f"Qual é a melhor forma de começar a estudar o diploma {law_label}?",
            "options": [
                "Ler apenas o título",
                "Identificar o objeto, o âmbito de aplicação e os artigos principais",
                "Ignorar os artigos",
                "Ler apenas diplomas relacionados",
            ],
            "correct_option": 1,
            "expected_answer": "Identificar o objeto, o âmbito de aplicação e os artigos principais.",
            "explanation": "O objeto e o âmbito ajudam a perceber para que serve a lei e a quem se aplica.",
        },
        {
            "type": "short_answer",
            "question": f"O que deves tentar identificar no objeto do diploma {law_label}?",
            "options": [],
            "correct_option": None,
            "expected_answer": "Deve identificar o que o diploma regula e qual é a sua finalidade principal.",
            "explanation": "O objeto mostra a finalidade central do diploma.",
        },
        {
            "type": "multiple_choice",
            "question": "Porque é importante analisar as relações entre diplomas?",
            "options": [
                "Porque uma lei pode citar, alterar, revogar ou complementar outra",
                "Porque todos os diplomas são independentes",
                "Porque as citações não têm relevância",
                "Porque evita ler o texto da lei",
            ],
            "correct_option": 0,
            "expected_answer": "As relações mostram se uma lei cita, altera, revoga ou complementa outra.",
            "explanation": "O grafo legal ajuda a perceber dependências entre diplomas.",
        },
        {
            "type": "short_answer",
            "question": "O que significa dizer que um diploma cita outro diploma?",
            "options": [],
            "correct_option": None,
            "expected_answer": "Significa que o diploma faz referência expressa a outro diploma no seu texto.",
            "explanation": "Uma citação indica uma ligação textual ou jurídica entre diplomas.",
        },
        {
            "type": "multiple_choice",
            "question": "O que significa uma relação de alteração entre diplomas?",
            "options": [
                "Um diploma modifica o conteúdo jurídico de outro",
                "Um diploma ignora outro",
                "Um diploma elimina todos os anteriores",
                "Um diploma não tem relação com outro",
            ],
            "correct_option": 0,
            "expected_answer": "Um diploma altera ou modifica o conteúdo jurídico de outro diploma.",
            "explanation": "Alterar significa mudar a redação, o regime ou certos efeitos jurídicos.",
        },
        {
            "type": "short_answer",
            "question": "Porque é útil resumir uma lei antes de responder a perguntas sobre ela?",
            "options": [],
            "correct_option": None,
            "expected_answer": "Porque o resumo ajuda a compreender a finalidade, o âmbito e as regras principais da lei.",
            "explanation": "O resumo dá uma visão geral antes de analisar detalhes.",
        },
        {
            "type": "multiple_choice",
            "question": "O que deve ser evitado ao interpretar uma lei num chatbot jurídico?",
            "options": [
                "Usar apenas documentos indexados",
                "Indicar fontes",
                "Inventar artigos ou interpretações sem base no contexto",
                "Distinguir citações de alterações",
            ],
            "correct_option": 2,
            "expected_answer": "Deve evitar-se inventar artigos, prazos, datas ou interpretações sem base no contexto.",
            "explanation": "O sistema deve responder apenas com base nas fontes disponíveis.",
        },
        {
            "type": "short_answer",
            "question": "O que é uma fonte consultada no contexto do chatbot jurídico?",
            "options": [],
            "correct_option": None,
            "expected_answer": "É um excerto ou documento usado pelo sistema para fundamentar a resposta.",
            "explanation": "As fontes mostram de onde veio a informação usada na resposta.",
        },
        {
            "type": "multiple_choice",
            "question": "O que representa um cluster no grafo legal?",
            "options": [
                "Uma categoria jurídica oficial",
                "Um agrupamento automático de diplomas com ligações entre si",
                "Uma lista de leis revogadas",
                "Um índice do Diário da República",
            ],
            "correct_option": 1,
            "expected_answer": "Um cluster é um agrupamento automático de diplomas ligados no grafo.",
            "explanation": "Os clusters são comunidades estruturais, não categorias jurídicas oficiais.",
        },
        {
            "type": "short_answer",
            "question": "Qual é a vantagem de estudar uma lei juntamente com os diplomas que ela cita?",
            "options": [],
            "correct_option": None,
            "expected_answer": "Permite compreender melhor o enquadramento jurídico e as dependências da lei.",
            "explanation": "As citações ajudam a perceber o contexto e as ligações legais.",
        },
    ]

    questions = []

    while len(questions) < num_questions:
        questions.extend(base_questions)

    return {
        "title": f"Quiz sobre {law_label}",
        "questions": questions[:num_questions],
    }


def generate_interactive_quiz(text_context: str, law_label: str, num_questions: int = 6) -> dict | None:
    prompt = f"""
Tu és um gerador de quizzes jurídicos.

Tarefa:
Cria um quiz interativo para estudantes sobre {law_label}, usando APENAS o contexto fornecido.

Regras obrigatórias:
- Responde APENAS com JSON válido.
- Não uses markdown.
- Não uses ```json.
- Não escrevas texto antes nem depois do JSON.
- Não inventes informação fora do contexto.
- Cria exatamente {num_questions} perguntas.
- Mistura perguntas de escolha múltipla e resposta curta.
- Pelo menos metade devem ser de escolha múltipla.
- As opções de escolha múltipla devem ser plausíveis.
- O índice correct_option começa em 0.
- Para perguntas de resposta curta, correct_option deve ser null.
- Para resposta curta, options deve ser [].

Formato obrigatório:
{{
  "title": "Quiz sobre {law_label}",
  "questions": [
    {{
      "type": "multiple_choice",
      "question": "Pergunta aqui",
      "options": ["Opção A", "Opção B", "Opção C", "Opção D"],
      "correct_option": 0,
      "expected_answer": "Resposta esperada",
      "explanation": "Explicação curta"
    }},
    {{
      "type": "short_answer",
      "question": "Pergunta aqui",
      "options": [],
      "correct_option": null,
      "expected_answer": "Resposta esperada",
      "explanation": "Explicação curta"
    }}
  ]
}}

CONTEXTO:
{text_context}
"""

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Responde apenas com JSON válido. Não uses markdown.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options={
                "temperature": 0.05,
                "top_p": 0.8,
            },
        )

        content = response["message"]["content"]
        parsed = extract_json_from_text(content)

        if parsed and validate_quiz_json(parsed, expected_num_questions=num_questions):
            return parsed

        repair_prompt = f"""
O texto seguinte devia ser JSON válido de um quiz, mas pode estar mal formatado ou ter número errado de perguntas.

Converte-o para JSON válido seguindo exatamente este formato e com exatamente {num_questions} perguntas:
{{
  "title": "Quiz sobre {law_label}",
  "questions": [
    {{
      "type": "multiple_choice",
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "correct_option": 0,
      "expected_answer": "...",
      "explanation": "..."
    }}
  ]
}}

Regras:
- Responde APENAS com JSON válido.
- Não uses markdown.
- Não escrevas texto fora do JSON.
- Tem de ter exatamente {num_questions} perguntas.

TEXTO A REPARAR:
{content}
"""

        repair_response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Repara e devolve apenas JSON válido.",
                },
                {
                    "role": "user",
                    "content": repair_prompt,
                },
            ],
            options={
                "temperature": 0.0,
                "top_p": 0.8,
            },
        )

        repaired = extract_json_from_text(repair_response["message"]["content"])

        if repaired and validate_quiz_json(repaired, expected_num_questions=num_questions):
            return repaired

    except Exception:
        pass

    return fallback_quiz(law_label, num_questions=num_questions)


def evaluate_short_answer(question: str, expected_answer: str, student_answer: str, context: str) -> dict:
    prompt = f"""
Avalia a resposta de um estudante a uma pergunta jurídica.

Regras:
- Usa apenas a pergunta, a resposta esperada e o contexto.
- Não exijas palavras exatamente iguais.
- Avalia se a ideia principal está correta.
- score deve ser 0, 0.5 ou 1.
- Responde APENAS com JSON válido.
- Não uses markdown.
- Não escrevas texto fora do JSON.

Formato obrigatório:
{{
  "is_correct": true,
  "score": 1,
  "feedback": "Feedback curto em português"
}}

PERGUNTA:
{question}

RESPOSTA ESPERADA:
{expected_answer}

RESPOSTA DO ESTUDANTE:
{student_answer}

CONTEXTO:
{context}
"""

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "És um avaliador. Responde apenas com JSON válido.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options={
                "temperature": 0.0,
                "top_p": 0.8,
            },
        )

        content = response["message"]["content"]
        parsed = extract_json_from_text(content)

        if parsed and "score" in parsed and "feedback" in parsed:
            score = float(parsed.get("score", 0))

            if score not in [0, 0.5, 1]:
                if score >= 0.75:
                    score = 1
                elif score >= 0.25:
                    score = 0.5
                else:
                    score = 0

            return {
                "is_correct": bool(score >= 0.5),
                "score": score,
                "feedback": str(parsed.get("feedback", "")),
            }

    except Exception:
        pass

    expected_words = set(normalize_for_match(expected_answer).split())
    student_words = set(normalize_for_match(student_answer).split())

    overlap = len(expected_words & student_words)

    if overlap >= 3:
        return {
            "is_correct": True,
            "score": 0.5,
            "feedback": "A resposta parece tocar em alguns elementos relevantes, mas deve ser revista.",
        }

    return {
        "is_correct": False,
        "score": 0,
        "feedback": "Não consegui confirmar que a resposta contém a ideia principal esperada.",
    }


def render_interactive_quiz(quiz: dict, text_context: str, key_prefix: str = "quiz"):
    st.markdown(f"### {quiz.get('title', 'Quiz')}")

    questions = quiz.get("questions", [])

    if not questions:
        st.info("Este quiz não tem perguntas.")
        return

    total_questions = len(questions)

    current_key = f"{key_prefix}_current_question"
    score_key = f"{key_prefix}_score"
    answered_key = f"{key_prefix}_answered"
    results_key = f"{key_prefix}_results"
    finished_key = f"{key_prefix}_finished"

    if current_key not in st.session_state:
        st.session_state[current_key] = 0

    if score_key not in st.session_state:
        st.session_state[score_key] = 0.0

    if answered_key not in st.session_state:
        st.session_state[answered_key] = False

    if results_key not in st.session_state:
        st.session_state[results_key] = []

    if finished_key not in st.session_state:
        st.session_state[finished_key] = False

    if st.session_state[finished_key]:
        st.markdown("## Resultado final")

        final_score = st.session_state[score_key]
        percentage = round((final_score / total_questions) * 100, 1)

        st.markdown(f"### {final_score}/{total_questions} ({percentage}%)")

        if percentage >= 80:
            st.success("Muito bom! Estás a dominar bem este diploma.")
        elif percentage >= 50:
            st.warning("Bom começo. Vale a pena rever alguns pontos.")
        else:
            st.error("Ainda precisas de rever melhor o conteúdo da lei.")

        st.markdown("## Revisão das respostas")

        for i, result in enumerate(st.session_state[results_key], start=1):
            st.markdown(f"### Pergunta {i}")
            st.write(f"**Pergunta:** {result['question']}")
            st.write(f"**A tua resposta:** {result['student_answer']}")
            st.write(f"**Resposta esperada:** {result['expected_answer']}")
            st.write(f"**Pontuação:** {result['score']}/1")
            st.write(f"**Feedback:** {result['feedback']}")

            if result["score"] >= 1:
                st.success("Correto ✅")
            elif result["score"] >= 0.5:
                st.warning("Parcialmente correto ⚠️")
            else:
                st.error("Errado ❌")

            st.markdown("---")

        if st.button("Recomeçar quiz"):
            st.session_state[current_key] = 0
            st.session_state[score_key] = 0.0
            st.session_state[answered_key] = False
            st.session_state[results_key] = []
            st.session_state[finished_key] = False
            st.rerun()

        return

    current_index = st.session_state[current_key]
    q = questions[current_index]

    progress_value = current_index / total_questions
    st.progress(progress_value)

    st.markdown(f"## Pergunta {current_index + 1} de {total_questions}")

    with st.container(border=True):
        st.write(q.get("question", ""))

        q_type = q.get("type", "short_answer")
        answer_key = f"{key_prefix}_answer_{current_index}"

        if q_type == "multiple_choice":
            options = q.get("options", [])

            if not options:
                st.warning("Esta pergunta de escolha múltipla não tem opções.")
                student_answer = ""
            else:
                student_answer = st.radio(
                    "Escolhe uma opção:",
                    options,
                    key=answer_key,
                    disabled=st.session_state[answered_key],
                )

        else:
            student_answer = st.text_area(
                "A tua resposta:",
                key=answer_key,
                height=100,
                disabled=st.session_state[answered_key],
            )

        col1, col2, col3 = st.columns([1, 1, 4])

        with col1:
            submit = st.button(
                "Submeter resposta",
                key=f"{key_prefix}_submit_{current_index}",
                disabled=st.session_state[answered_key],
            )

        with col2:
            next_question = st.button(
                "Próxima pergunta",
                key=f"{key_prefix}_next_{current_index}",
                disabled=not st.session_state[answered_key],
            )

    if submit:
        expected_answer = q.get("expected_answer", "")
        explanation = q.get("explanation", "")

        if q_type == "multiple_choice":
            options = q.get("options", [])
            correct_option = q.get("correct_option", None)

            selected_index = options.index(student_answer) if student_answer in options else -1
            correct = selected_index == correct_option
            score = 1 if correct else 0

            if correct_option is not None and 0 <= correct_option < len(options):
                correct_answer = options[correct_option]
            else:
                correct_answer = expected_answer

            feedback = explanation or (
                "Resposta correta." if correct else "Resposta incorreta."
            )

        else:
            if not str(student_answer).strip():
                score = 0
                correct_answer = expected_answer
                feedback = "Não escreveste uma resposta suficiente para avaliar."
            else:
                evaluation = evaluate_short_answer(
                    q.get("question", ""),
                    expected_answer,
                    student_answer,
                    text_context,
                )

                score = float(evaluation.get("score", 0))
                correct_answer = expected_answer
                feedback = evaluation.get("feedback", "")

        st.session_state[score_key] += score
        st.session_state[answered_key] = True

        st.session_state[results_key].append(
            {
                "question": q.get("question", ""),
                "student_answer": student_answer,
                "expected_answer": correct_answer,
                "score": score,
                "feedback": feedback,
            }
        )

        st.rerun()

    if st.session_state[answered_key]:
        latest_result = st.session_state[results_key][-1]

        st.markdown("## Correção")

        if latest_result["score"] >= 1:
            st.success("Correto ✅")
        elif latest_result["score"] >= 0.5:
            st.warning("Parcialmente correto ⚠️")
        else:
            st.error("Errado ❌")

        st.write(f"**Pontuação:** {latest_result['score']}/1")
        st.write(f"**Resposta correta/esperada:** {latest_result['expected_answer']}")
        st.write(f"**Feedback:** {latest_result['feedback']}")

    if next_question:
        if current_index + 1 >= total_questions:
            st.session_state[finished_key] = True
        else:
            st.session_state[current_key] += 1
            st.session_state[answered_key] = False

        st.rerun()


# ============================================================
# Visualização e exploração do grafo
# ============================================================

def build_filtered_graph(edges_df: pd.DataFrame, nodes_df: pd.DataFrame) -> nx.DiGraph:
    graph = nx.DiGraph()

    for _, row in nodes_df.iterrows():
        node_id = safe_str(row.get("node_id", ""))

        if not node_id:
            continue

        graph.add_node(
            node_id,
            label=safe_str(row.get("label", "")),
            node_type=safe_str(row.get("node_type", "")),
            theme=safe_str(row.get("theme", "")),
            pdf_path=safe_str(row.get("pdf_path", "")),
        )

    for _, row in edges_df.iterrows():
        source_id = safe_str(row.get("source_id", ""))
        target_id = safe_str(row.get("target_id", ""))
        source_label = safe_str(row.get("source_label", ""))
        target_label = safe_str(row.get("target_label", ""))

        if not source_id or not target_id:
            continue

        if source_id == target_id:
            continue

        if normalize_for_match(source_label) == normalize_for_match(target_label):
            continue

        graph.add_edge(
            source_id,
            target_id,
            weight=int(float(row.get("weight", 1) or 1)),
            relation_type=safe_str(row.get("relation_type", "cites")),
            source_label=source_label,
            target_label=target_label,
            contexts_sample=safe_str(row.get("contexts_sample", "")),
        )

    return graph


def dataframe_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if df.empty or not query.strip():
        return df

    query = query.lower()
    mask = pd.Series(False, index=df.index)

    for column in df.columns:
        mask = mask | df[column].astype(str).str.lower().str.contains(re.escape(query), na=False)

    return df[mask]


def get_node_display_label(graph: nx.DiGraph, node_id: str) -> str:
    attrs = graph.nodes[node_id]
    label = clean_label_for_display(attrs.get("label", node_id))

    if not label:
        label = node_id

    return label


def get_node_lookup_options(graph: nx.DiGraph) -> dict[str, str]:
    options = {}

    for node_id in graph.nodes():
        label = get_node_display_label(graph, node_id)
        degree = graph.degree(node_id, weight="weight")
        theme = safe_str(graph.nodes[node_id].get("theme", ""))

        display = f"{label} | grau: {degree}"

        if theme:
            display += f" | tema: {theme}"

        options[display] = node_id

    return dict(sorted(options.items(), key=lambda item: item[0].lower()))


def get_incident_edges_df(graph: nx.DiGraph, node_id: str) -> pd.DataFrame:
    rows = []

    for source, target, data in graph.out_edges(node_id, data=True):
        rows.append(
            {
                "direction": "sai",
                "source_id": source,
                "source_label": clean_label_for_display(data.get("source_label", graph.nodes[source].get("label", source))),
                "target_id": target,
                "target_label": clean_label_for_display(data.get("target_label", graph.nodes[target].get("label", target))),
                "relation_type": data.get("relation_type", ""),
                "relation_label": RELATION_LABELS.get(data.get("relation_type", ""), data.get("relation_type", "")),
                "weight": data.get("weight", 1),
                "contexts_sample": data.get("contexts_sample", ""),
            }
        )

    for source, target, data in graph.in_edges(node_id, data=True):
        rows.append(
            {
                "direction": "entra",
                "source_id": source,
                "source_label": clean_label_for_display(data.get("source_label", graph.nodes[source].get("label", source))),
                "target_id": target,
                "target_label": clean_label_for_display(data.get("target_label", graph.nodes[target].get("label", target))),
                "relation_type": data.get("relation_type", ""),
                "relation_label": RELATION_LABELS.get(data.get("relation_type", ""), data.get("relation_type", "")),
                "weight": data.get("weight", 1),
                "contexts_sample": data.get("contexts_sample", ""),
            }
        )

    return pd.DataFrame(rows)


def render_node_inspector(
    graph: nx.DiGraph,
    node_to_cluster: dict[str, int] | None = None,
    title: str = "Inspecionar nó",
):
    st.markdown(f"### {title}")

    if graph.number_of_nodes() == 0:
        st.info("Não há nós para inspecionar.")
        return

    options = get_node_lookup_options(graph)

    selected_label = st.selectbox(
        "Escolhe um nó/diploma",
        list(options.keys()),
        key=f"node_inspector_{title}",
    )

    node_id = options[selected_label]
    attrs = graph.nodes[node_id]
    cluster_id = node_to_cluster.get(node_id, "") if node_to_cluster else ""

    st.markdown("#### Informação do nó")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Grau total", graph.degree(node_id, weight="weight"))
    c2.metric("Relações que entram", graph.in_degree(node_id, weight="weight"))
    c3.metric("Relações que saem", graph.out_degree(node_id, weight="weight"))
    c4.metric("Cluster", cluster_id if cluster_id != "" else "N/A")

    st.write(f"**Nó ID:** `{node_id}`")
    st.write(f"**Diploma / etiqueta:** {clean_label_for_display(attrs.get('label', node_id))}")
    st.write(f"**Tipo de nó:** `{attrs.get('node_type', '')}`")
    st.write(f"**Tema:** `{attrs.get('theme', '')}`")
    st.write(f"**Ficheiro/PDF:** `{attrs.get('pdf_path', '')}`")

    incident_df = get_incident_edges_df(graph, node_id)

    if incident_df.empty:
        st.info("Este nó não tem relações no subgrafo atual.")
        return

    st.markdown("#### Relações deste nó")

    display_df = incident_df[
        [
            "direction",
            "source_label",
            "target_label",
            "relation_label",
            "weight",
            "contexts_sample",
        ]
    ].copy()

    display_df["contexts_sample"] = display_df["contexts_sample"].apply(lambda value: shorten(str(value), 300))

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Ver detalhes completos das relações"):
        for i, row in incident_df.iterrows():
            st.markdown(f"##### Relação {i + 1}")

            st.write(f"**Direção:** {row['direction']}")
            st.write(f"**Origem:** {row['source_label']}")
            st.write(f"**Destino:** {row['target_label']}")
            st.write(f"**Tipo de relação:** {row['relation_label']}")
            st.write(f"**Peso:** {row['weight']}")
            st.write("**Contexto textual extraído:**")
            st.info(row["contexts_sample"] or "Sem contexto textual guardado.")
            st.markdown("---")


def render_plotly_graph(
    graph: nx.DiGraph,
    node_to_cluster: dict[str, int] | None = None,
    max_nodes: int = 80,
):
    if graph.number_of_nodes() == 0:
        st.info("Ainda não há ligações suficientes para desenhar o grafo.")
        return

    original_nodes = graph.number_of_nodes()

    if graph.number_of_nodes() > max_nodes:
        ranked = sorted(
            graph.degree(weight="weight"),
            key=lambda item: item[1],
            reverse=True,
        )[:max_nodes]
        keep = {node for node, _ in ranked}
        graph = graph.subgraph(keep).copy()

        st.caption(
            f"A mostrar os {graph.number_of_nodes()} nós mais conectados de {original_nodes}. "
            "Usa os filtros ou o modo por diploma/pergunta para focar melhor."
        )

    pos = nx.spring_layout(graph, k=0.75, iterations=80, seed=42, weight="weight")

    edge_x = []
    edge_y = []
    edge_hover = []

    for source, target, data in graph.edges(data=True):
        x0, y0 = pos[source]
        x1, y1 = pos[target]

        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

        relation = RELATION_LABELS.get(data.get("relation_type", ""), data.get("relation_type", ""))
        source_label = clean_label_for_display(data.get("source_label", source))
        target_label = clean_label_for_display(data.get("target_label", target))

        edge_hover.append(
            f"{source_label} → {target_label}<br>"
            f"Relação: {relation}<br>"
            f"Peso: {data.get('weight', 1)}"
        )

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=0.8),
        hoverinfo="none",
        mode="lines",
    )

    node_x = []
    node_y = []
    node_text = []
    node_labels = []
    node_size = []
    node_symbol = []
    node_color = []

    degrees = dict(graph.degree(weight="weight"))

    for node in graph.nodes():
        x, y = pos[node]
        attrs = graph.nodes[node]

        degree = degrees.get(node, 0)
        label = clean_label_for_display(attrs.get("label", node))
        node_type = attrs.get("node_type", "")
        theme = attrs.get("theme", "")
        pdf_path = attrs.get("pdf_path", "")
        cluster_id = node_to_cluster.get(node, 0) if node_to_cluster else 0

        incoming = graph.in_degree(node, weight="weight")
        outgoing = graph.out_degree(node, weight="weight")

        node_x.append(x)
        node_y.append(y)

        node_text.append(
            f"<b>{label}</b><br>"
            f"ID: {node}<br>"
            f"Tipo: {node_type}<br>"
            f"Tema: {theme}<br>"
            f"PDF: {pdf_path}<br>"
            f"Grau total: {degree}<br>"
            f"Entram: {incoming}<br>"
            f"Saem: {outgoing}<br>"
            f"Cluster: {cluster_id}"
        )

        node_labels.append(label[:35])
        node_size.append(10 + min(40, degree * 2))
        node_symbol.append("circle" if node_type == "source_document" else "diamond")
        node_color.append(cluster_id)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_labels,
        textposition="top center",
        hovertext=node_text,
        hoverinfo="text",
        marker=dict(
            size=node_size,
            symbol=node_symbol,
            color=node_color,
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Cluster"),
            line=dict(width=1),
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            height=720,
            showlegend=False,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            hovermode="closest",
        ),
    )

    st.plotly_chart(fig, use_container_width=True)


def display_edges_table(edges_result: pd.DataFrame):
    if edges_result.empty:
        return

    display_cols = [
        "source_label",
        "target_label",
        "relation_type",
        "weight",
        "contexts_sample",
    ]

    existing_cols = [col for col in display_cols if col in edges_result.columns]
    display_df = edges_result[existing_cols].copy()

    if "source_label" in display_df.columns:
        display_df["source_label"] = display_df["source_label"].apply(clean_label_for_display)

    if "target_label" in display_df.columns:
        display_df["target_label"] = display_df["target_label"].apply(clean_label_for_display)

    if "relation_type" in display_df.columns:
        display_df["relation_type"] = display_df["relation_type"].map(
            lambda value: RELATION_LABELS.get(value, value)
        )

    if "contexts_sample" in display_df.columns:
        display_df["contexts_sample"] = display_df["contexts_sample"].apply(lambda value: shorten(str(value), 300))

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )


def summarize_edges_for_display(edges_df: pd.DataFrame) -> str:
    if edges_df.empty:
        return ""

    lines = []

    if "pair" in edges_df.columns:
        for pair, group in edges_df.groupby("pair"):
            lines.append(f"\nPar: {pair}")

            for relation_type, rel_group in group.groupby("relation_type"):
                relation_label = RELATION_LABELS.get(relation_type, relation_type)
                lines.append(f"  Relação: {relation_label}")

                for _, row in rel_group.iterrows():
                    lines.append(f"  - Peso: {row.get('weight', 1)}")

        return "\n".join(lines)

    for relation_type, group in edges_df.groupby("relation_type"):
        relation_label = RELATION_LABELS.get(relation_type, relation_type)
        lines.append(f"\nRelação: {relation_label}")

        for _, row in group.iterrows():
            direction = row.get("direction", "")
            weight = row.get("weight", 1)

            if direction == "outgoing":
                other = row.get("target_label", "")
            else:
                other = row.get("source_label", "")

            lines.append(f"- {clean_label_for_display(other)} | peso: {weight}")

    return "\n".join(lines)


def render_sources(retrieved: list[dict[str, Any]]):
    st.subheader("Fontes consultadas")

    if not retrieved:
        st.info("Nenhuma fonte textual encontrada.")
        return

    for i, item in enumerate(retrieved, start=1):
        meta = item["metadata"]
        title = meta.get("title", "Sem título")
        article = meta.get("article_id", "")
        matches = item.get("matches_specific_diploma", False)
        reason = item.get("source_reason", "")

        label = f"Fonte {i}: {clean_label_for_display(title)}"

        if article:
            label += f" — Artigo {article}"

        if matches:
            label += " ✅"

        with st.expander(label):
            st.write(f"**Motivo:** `{reason}`")
            st.write(f"**Tema:** {meta.get('theme', '')}")
            st.write(f"**Diploma:** {clean_label_for_display(title)}")
            st.write(f"**Artigo:** {article}")
            st.write(f"**Chunk:** `{meta.get('chunk_index', '')}`")
            st.write(f"**Subchunk:** `{meta.get('subchunk_index', '')}`")
            st.write(f"**PDF:** `{meta.get('pdf_path', '')}`")
            st.write(f"**Distância vetorial:** `{item.get('distance', '')}`")

            st.text_area(
                "Excerto",
                item["text"],
                height=240,
                key=f"retrieved_{i}_{reason}_{meta.get('chunk_index', '')}_{meta.get('subchunk_index', '')}_{article}",
            )


# ============================================================
# Main app
# ============================================================

def main():
    st.set_page_config(
        page_title="Legal Network Agent",
        page_icon="⚖️",
        layout="wide",
    )

    st.title("⚖️ Legal Network Agent")
    st.caption("RAG + GraphRAG + Clustering + Tutor jurídico interativo para explorar legislação portuguesa.")

    with st.sidebar:
        st.header("Configuração")
        st.write(f"**ChromaDB:** `{CHROMA_DIR}`")
        st.write(f"**Coleção:** `{COLLECTION_NAME}`")
        st.write(f"**Embeddings:** `{EMBED_MODEL}`")
        st.write(f"**LLM:** `{LLM_MODEL}`")

        n_results = st.slider("Excertos por pergunta", 3, 15, 6)

        st.markdown("---")
        st.warning("Protótipo exploratório. Não substitui aconselhamento jurídico profissional.")

    if not CHROMA_DIR.exists():
        st.error("Não existe ChromaDB. Corre primeiro: py index_pdfs.py")
        return

    edges_df, nodes_df, metrics_df, graph = load_graph_data()
    node_to_cluster, clusters_df = compute_graph_clusters(graph)

    tabs = st.tabs(
        [
            "📌 Visão geral",
            "🕸️ Rede de dependências",
            "🧩 Clusters",
            "📚 Estudar lei",
            "📝 Quiz interativo",
            "🔎 Explorador",
            "💬 Assistente",
        ]
    )

    with tabs[0]:
        st.subheader("Estado do sistema")

        collection = load_collection()
        total_chunks = collection.count()

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("Chunks na ChromaDB", total_chunks)
        c2.metric("Nós no grafo", graph.number_of_nodes())
        c3.metric("Ligações no grafo", graph.number_of_edges())
        c4.metric("Diplomas no grafo", nodes_df["label"].nunique() if not nodes_df.empty else 0)
        c5.metric("Clusters", clusters_df["cluster_id"].nunique() if not clusters_df.empty else 0)

        if not metrics_df.empty:
            st.subheader("Diplomas mais centrais")
            st.dataframe(metrics_df.head(20), use_container_width=True, hide_index=True)

    with tabs[1]:
        st.subheader("Rede de dependências legais")

        if graph.number_of_nodes() == 0:
            st.info("Ainda não existe grafo. Corre: py build_legal_graph.py")
        else:
            graph_mode = st.radio(
                "Modo de visualização",
                ["Grafo completo", "Grafo por diploma", "Grafo por pergunta"],
                horizontal=True,
            )

            relation_options = sorted(edges_df["relation_type"].dropna().unique()) if not edges_df.empty else []

            selected_relations = st.multiselect(
                "Filtrar por tipo de relação",
                relation_options,
                default=relation_options,
                format_func=lambda value: RELATION_LABELS.get(value, value),
            )

            filtered_edges = edges_df.copy()

            if not filtered_edges.empty and selected_relations:
                filtered_edges = filtered_edges[filtered_edges["relation_type"].isin(selected_relations)]

            filtered_graph = build_filtered_graph(filtered_edges, nodes_df)

            current_graph = filtered_graph

            if graph_mode == "Grafo completo":
                st.info(
                    "Dica: passa o rato por cima dos nós para veres tema, ficheiro, cluster e grau. "
                    "Usa o painel de inspeção abaixo para ver relações detalhadas."
                )

                render_plotly_graph(filtered_graph, node_to_cluster=node_to_cluster, max_nodes=120)
                current_graph = filtered_graph

            elif graph_mode == "Grafo por diploma":
                selected_query = st.text_input(
                    "Diploma para focar",
                    placeholder="Ex: Decreto-Lei n.º 30/2018",
                )

                depth = st.slider("Profundidade da rede", 1, 3, 1)

                if selected_query.strip():
                    selected_diploma = extract_specific_diploma_query(selected_query)

                    if not selected_diploma:
                        st.warning("Não consegui detetar o diploma. Tenta: Decreto-Lei n.º 30/2018")
                        current_graph = nx.DiGraph()
                    else:
                        subgraph = build_contextual_subgraph(filtered_graph, selected_diploma, depth=depth)

                        if subgraph.number_of_nodes() == 0:
                            st.warning("Não encontrei esse diploma no grafo.")
                            current_graph = nx.DiGraph()
                        else:
                            st.success(f"Grafo contextual para: {selected_diploma['raw']}")
                            render_plotly_graph(subgraph, node_to_cluster=node_to_cluster, max_nodes=160)
                            current_graph = subgraph
                else:
                    st.info("Escreve um diploma para gerar o grafo contextual.")
                    current_graph = nx.DiGraph()

            else:
                prompt_query = st.text_input(
                    "Pergunta ou lista de diplomas",
                    placeholder="Ex: relação entre Decreto-Lei n.º 30/2018, Decreto-Lei n.º 17/2018 e Decreto-Lei n.º 18/2008",
                )

                include_neighbors = st.checkbox("Incluir vizinhos próximos", value=True)
                depth = st.slider("Profundidade dos vizinhos", 1, 3, 1, key="prompt_graph_depth")

                if prompt_query.strip():
                    diplomas = extract_all_diplomas_from_question(prompt_query)

                    if not diplomas:
                        st.warning("Não detetei diplomas na pergunta.")
                        current_graph = nx.DiGraph()
                    else:
                        st.write("Diplomas detetados:")

                        for diploma in diplomas:
                            st.write(f"- {diploma['raw']}")

                        subgraph = build_multi_diploma_subgraph(
                            filtered_graph,
                            diplomas,
                            include_neighbors=include_neighbors,
                            depth=depth,
                        )

                        if subgraph.number_of_nodes() == 0:
                            st.warning("Não consegui construir subgrafo para estes diplomas.")
                            current_graph = nx.DiGraph()
                        else:
                            render_plotly_graph(subgraph, node_to_cluster=node_to_cluster, max_nodes=180)
                            current_graph = subgraph
                else:
                    st.info("Escreve uma pergunta com um ou mais diplomas.")
                    current_graph = nx.DiGraph()

            st.markdown("---")
            render_node_inspector(
                current_graph,
                node_to_cluster=node_to_cluster,
                title="Inspecionar nó do grafo atual",
            )

    with tabs[2]:
        st.subheader("Clusters / comunidades no grafo legal")

        if clusters_df.empty:
            st.info("Não foi possível calcular clusters.")
        else:
            st.write(
                "Os clusters são comunidades estruturais detetadas automaticamente no grafo, "
                "com base nas ligações entre diplomas. Não são categorias jurídicas oficiais."
            )

            st.dataframe(clusters_df, use_container_width=True, hide_index=True)

            selected_cluster = st.selectbox(
                "Ver cluster",
                clusters_df["cluster_id"].tolist(),
            )

            cluster_nodes = [
                node for node, cluster_id in node_to_cluster.items()
                if cluster_id == selected_cluster
            ]

            cluster_graph = graph.subgraph(cluster_nodes).copy()

            st.markdown(f"### Grafo do Cluster {selected_cluster}")
            render_plotly_graph(cluster_graph, node_to_cluster=node_to_cluster, max_nodes=160)

            st.markdown("---")
            render_node_inspector(
                cluster_graph,
                node_to_cluster=node_to_cluster,
                title=f"Inspecionar nó do Cluster {selected_cluster}",
            )

            incident_rows = []

            for source, target, data in cluster_graph.edges(data=True):
                incident_rows.append(
                    {
                        "origem": clean_label_for_display(data.get("source_label", source)),
                        "destino": clean_label_for_display(data.get("target_label", target)),
                        "tipo_relacao": RELATION_LABELS.get(data.get("relation_type", ""), data.get("relation_type", "")),
                        "peso": data.get("weight", 1),
                        "contexto": shorten(data.get("contexts_sample", ""), 350),
                    }
                )

            if incident_rows:
                st.markdown("### Relações dentro deste cluster")
                st.dataframe(pd.DataFrame(incident_rows), use_container_width=True, hide_index=True)

    with tabs[3]:
        st.subheader("📚 Estudar uma lei")

        study_law = st.text_input(
            "Que diploma queres estudar?",
            placeholder="Ex: Decreto-Lei n.º 30/2018",
        )

        study_mode = st.radio(
            "Modo de estudo",
            [
                "Resumo simples",
                "Resumo + conceitos-chave",
                "Flashcards",
            ],
            horizontal=True,
        )

        study_button = st.button("Gerar material de estudo", type="primary")

        if study_button and study_law.strip():
            if study_mode == "Resumo simples":
                question = f"Explica {study_law} em linguagem simples para estudantes."
            elif study_mode == "Resumo + conceitos-chave":
                question = f"Faz um resumo para estudantes de {study_law} e identifica os conceitos-chave."
            else:
                question = f"Cria flashcards para estudar {study_law}, com pergunta e resposta."

            with st.spinner("A preparar material de estudo..."):
                retrieved, graph_context, edges_result, fallback_used = retrieve_context(
                    question,
                    graph,
                    edges_df,
                    clusters_df,
                    node_to_cluster,
                    n_results=max(n_results, 10),
                )

                text_context = build_text_context(retrieved)

                answer = ask_llm(
                    question,
                    text_context,
                    graph_context,
                    fallback_used=fallback_used,
                )

            st.markdown("### Material de estudo")
            st.write(answer)

            render_sources(retrieved)

    with tabs[4]:
        st.subheader("📝 Quiz interativo")

        quiz_law = st.text_input(
            "Sobre que diploma queres fazer o quiz?",
            placeholder="Ex: Decreto-Lei n.º 30/2018",
            key="quiz_law_input",
        )

        quiz_num = st.slider(
            "Número de perguntas",
            min_value=3,
            max_value=10,
            value=6,
            key="quiz_num_slider",
        )

        col_a, col_b = st.columns([1, 4])

        with col_a:
            generate_quiz_button = st.button("Gerar quiz", type="primary")

        with col_b:
            clear_quiz_button = st.button("Limpar quiz")

        if clear_quiz_button:
            for key in [
                "interactive_quiz",
                "interactive_quiz_context",
                "interactive_quiz_sources",
                "interactive_quiz_current_question",
                "interactive_quiz_score",
                "interactive_quiz_answered",
                "interactive_quiz_results",
                "interactive_quiz_finished",
            ]:
                st.session_state.pop(key, None)

            st.rerun()

        if generate_quiz_button and quiz_law.strip():
            diploma = extract_specific_diploma_query(quiz_law)

            if not diploma:
                st.warning("Não consegui detetar o diploma. Exemplo: Decreto-Lei n.º 30/2018")
            else:
                question = f"Cria um quiz interativo para estudantes sobre {diploma['raw']}."

                with st.spinner("A procurar conteúdo da lei..."):
                    retrieved, graph_context, edges_result, fallback_used = retrieve_context(
                        question,
                        graph,
                        edges_df,
                        clusters_df,
                        node_to_cluster,
                        n_results=max(n_results, 12),
                    )

                    text_context = build_text_context(retrieved)

                with st.spinner("A gerar quiz interativo..."):
                    quiz = generate_interactive_quiz(
                        text_context=text_context,
                        law_label=diploma["raw"],
                        num_questions=quiz_num,
                    )

                if quiz is None:
                    st.error(
                        "Não consegui gerar um quiz estruturado. "
                        "Tenta novamente ou reduz o número de perguntas."
                    )
                else:
                    st.session_state["interactive_quiz"] = quiz
                    st.session_state["interactive_quiz_context"] = text_context
                    st.session_state["interactive_quiz_sources"] = retrieved

                    st.session_state["interactive_quiz_current_question"] = 0
                    st.session_state["interactive_quiz_score"] = 0.0
                    st.session_state["interactive_quiz_answered"] = False
                    st.session_state["interactive_quiz_results"] = []
                    st.session_state["interactive_quiz_finished"] = False

                    st.success("Quiz gerado!")

        if "interactive_quiz" in st.session_state:
            render_interactive_quiz(
                st.session_state["interactive_quiz"],
                st.session_state.get("interactive_quiz_context", ""),
                key_prefix="interactive_quiz",
            )

            with st.expander("Ver fontes usadas para gerar o quiz"):
                render_sources(st.session_state.get("interactive_quiz_sources", []))

    with tabs[5]:
        st.subheader("Explorador de relações")

        if edges_df.empty:
            st.info("Ainda não existem relações. Corre: py build_legal_graph.py")
        else:
            query = st.text_input("Pesquisar em relações")
            shown = dataframe_search(edges_df, query)

            table_cols = [
                "source_label",
                "target_label",
                "relation_type",
                "weight",
                "contexts_sample",
            ]

            existing = [col for col in table_cols if col in shown.columns]
            shown_display = shown[existing].copy()

            if "source_label" in shown_display.columns:
                shown_display["source_label"] = shown_display["source_label"].apply(clean_label_for_display)

            if "target_label" in shown_display.columns:
                shown_display["target_label"] = shown_display["target_label"].apply(clean_label_for_display)

            if "relation_type" in shown_display.columns:
                shown_display["relation_type"] = shown_display["relation_type"].map(
                    lambda value: RELATION_LABELS.get(value, value)
                )

            if "contexts_sample" in shown_display.columns:
                shown_display["contexts_sample"] = shown_display["contexts_sample"].apply(lambda value: shorten(str(value), 350))

            st.dataframe(shown_display, use_container_width=True, hide_index=True)

            st.download_button(
                "Descarregar relações filtradas em CSV",
                shown.to_csv(index=False).encode("utf-8-sig"),
                file_name="legal_network_edges.csv",
                mime="text/csv",
            )

    with tabs[6]:
        st.subheader("Assistente jurídico")

        question = st.text_area(
            "Pergunta",
            placeholder="Ex: Explica a relação entre Decreto-Lei n.º 30/2018 e Decreto-Lei n.º 17/2018.",
            height=110,
        )

        ask = st.button("Perguntar", type="primary")

        if ask and question.strip():
            diplomas = extract_all_diplomas_from_question(question)
            graph_question = is_graph_question(question)
            cluster_question = is_cluster_question(question)
            learning_question = is_learning_question(question)

            if diplomas:
                st.info(
                    "Diplomas detetados: "
                    + ", ".join(f"**{d['raw']}**" for d in diplomas)
                )
            else:
                st.warning(
                    "Não consegui detetar um diploma específico na pergunta. "
                    "Tenta escrever, por exemplo: Decreto-Lei n.º 30/2018 ou DL 30/2018."
                )

            if learning_question:
                st.info("Modo Tutor Jurídico ativado: resposta orientada para aprendizagem.")
            elif cluster_question:
                st.info("Modo Clustering ativado.")
            elif graph_question:
                st.info("Modo GraphRAG ativado: a pergunta parece ser sobre relações/correlações/dependências.")

            with st.spinner("A pesquisar contexto textual, relações legais e clusters..."):
                retrieved, graph_context, edges_result, fallback_used = retrieve_context(
                    question,
                    graph,
                    edges_df,
                    clusters_df,
                    node_to_cluster,
                    n_results=n_results,
                )

                text_context = build_text_context(retrieved)

            if graph_question and not graph_context:
                st.warning(
                    "A pergunta parece ser sobre relações legais, mas não encontrei relações suficientes no grafo."
                )

            if fallback_used:
                st.warning(
                    "Não foram encontradas relações exatamente do tipo pedido. "
                    "A mostrar outras relações legais associadas ao diploma."
                )

            with st.spinner("A gerar resposta..."):
                answer = ask_llm(
                    question,
                    text_context,
                    graph_context,
                    fallback_used=fallback_used,
                )

            st.markdown("### Resposta")
            st.write(answer)

            render_sources(retrieved)

            if graph_context:
                st.markdown("### Relações / clusters encontrados")
                st.text(graph_context)

            if graph_question and not edges_result.empty:
                st.markdown("### Resumo das relações")
                st.text(summarize_edges_for_display(edges_result))

                st.markdown("### Tabela de relações extraídas")
                display_edges_table(edges_result)


if __name__ == "__main__":
    main()