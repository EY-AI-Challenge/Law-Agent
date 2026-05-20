import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
from pyvis.network import Network

def build_semantic_graph(json_path, output_html, similarity_threshold=0.75):
    print("1. Loading Master Articles...")
    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)
        
    print(f"Loaded {len(articles)} articles.")

    # Prepare texts and metadata
    texts = []
    nodes_info = []
    
    for art in articles:
        # We embed the title + text for maximum semantic meaning
        full_text = f"{art['title']}. {art['text']}"
        texts.append(full_text)
        
        # Create a unique ID for the node
        node_id = f"{art['document']} - {art['article_id']}"
        nodes_info.append({
            "id": node_id,
            "label": art['article_id'],
            "title": f"{art['document']}\n{art['article_id']}: {art['title']}", # Hover text
            "category": art['category']
        })

    print("2. Generating Local Embeddings (This takes a few seconds)...")
    # Using a fast, multilingual model perfect for Portuguese
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    embeddings = model.encode(texts, show_progress_bar=True)

    print("3. Calculating Semantic Similarity...")
    sim_matrix = cosine_similarity(embeddings)

    print("4. Building the NetworkX Graph...")
    G = nx.Graph()

    # Add Nodes with EY Brand Colors
    for node in nodes_info:
        # EY Yellow for Labour, Dark Blue for Civil
        color = "#FFE600" if node["category"] == "labour" else "#1A1A24"
        font_color = "#000000" if node["category"] == "labour" else "#FFFFFF"
        
        G.add_node(
            node["id"], 
            label=node["label"], 
            title=node["title"], 
            color=color,
            font={"color": font_color}
        )

    # Add Edges based on Threshold
    edge_count = 0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            score = sim_matrix[i][j]
            if score >= similarity_threshold:
                # Add edge with weight/thickness based on similarity
                G.add_edge(nodes_info[i]["id"], nodes_info[j]["id"], value=float(score), title=f"Similarity: {score:.2f}")
                edge_count += 1

    print(f"Created {edge_count} semantic connections between laws.")

    print("5. Generating Interactive PyVis Map...")
    # Generate Physics-based interactive graph
    net = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="black")
    net.from_nx(G)
    
    # Add physics buttons for the UI
    net.show_buttons(filter_=['physics'])
    net.save_graph(output_html)
    
    print(f"✅ Success! Graph saved to {output_html}")

if __name__ == "__main__":
    # Point this to the output of your run_pipeline.py
    input_file = "output/master_articles.json"
    output_file = "legal_network.html"
    
    # Adjust threshold if you get too many or too few connections (0.70 to 0.85 is a good range)
    build_semantic_graph(input_file, output_file, similarity_threshold=0.75)