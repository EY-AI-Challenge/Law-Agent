import fitz  # PyMuPDF
import json
import os
import glob
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client()

# ==========================================
# PHASE 1: PARSING
# ==========================================
def clean_and_extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    clean_lines = []
    for page in doc:
        text = page.get_text("text")
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line == "LEGISLAÇÃO CONSOLIDADA" or line == "IMPRENSA NACIONAL CASA DA MOEDA":
                continue
            if line.startswith("Versão à data de") or "Pág." in line:
                continue
            clean_lines.append(line)
    return clean_lines

def chunk_into_articles(clean_lines, document_name, category):
    articles_dict = {} 
    current_article_id = None
    current_article_title = None
    current_article_text = []
    
    for i, line in enumerate(clean_lines):
        is_exact_article_header = line.startswith("Artigo ") and "º" in line and len(line) < 20
        
        if is_exact_article_header:
            if current_article_id:
                articles_dict[current_article_id] = {
                    "document": document_name,
                    "category": category, # Adds Civil or Labour tag!
                    "article_id": current_article_id,
                    "title": current_article_title,
                    "text": "\n".join(current_article_text).strip()
                }
            current_article_id = line
            current_article_title = clean_lines[i + 1] if i + 1 < len(clean_lines) else "Sem Título"
            current_article_text = []
        else:
            if current_article_id and line != current_article_title:
                current_article_text.append(line)
                
    if current_article_id:
        articles_dict[current_article_id] = {
            "document": document_name,
            "category": category,
            "article_id": current_article_id,
            "title": current_article_title,
            "text": "\n".join(current_article_text).strip()
        }
    return list(articles_dict.values())

# ==========================================
# PHASE 2: NLP EXTRACTION
# ==========================================
def extract_triplets_from_article(document_name, article_id, text):
    source_node = f"{article_id} do {document_name}"
    prompt = f"""
    You are an expert AI assistant specializing in Portuguese Law.
    Read the following text from a legal article. 
    Your task is to extract all explicit references to other laws, codes, decrees, or articles.
    
    Current Article (Source): "{source_node}"
    
    Text to analyze:
    "{text}"
    
    Return a raw JSON list of objects representing Knowledge Graph triplets. 
    Each object must have exactly these keys:
    - "source": always use "{source_node}"
    - "relationship": a short uppercase verb (e.g., "CITA", "ALTERA", "REVOGA", "APLICA-SE")
    - "target": the referenced law, code, or article (e.g., "Código do Trabalho", "Decreto-Lei n.º 433/99", "artigo 513.º")
    
    If there are NO references in the text, return an empty list: []
    Do NOT wrap the response in ```json markdown, just return the raw JSON array.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()
            
        triplets = json.loads(raw_text)
        return triplets
    except Exception as e:
        print(f"  [!] Extraction failed for {article_id}: {e}")
        return []

# ==========================================
# ORCHESTRATOR
# ==========================================
def main():
    folders = {"civil": "./civil", "labour": "./labour"}
    
    all_articles = []
    all_triplets = []
    
    # Ensure an output directory exists
    os.makedirs("output", exist_ok=True)
    
    # 1. Process all PDFs
    for category, folder_path in folders.items():
        if not os.path.exists(folder_path):
            print(f"⚠️ Folder {folder_path} not found. Skipping...")
            continue
            
        pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
        print(f"\n📁 Found {len(pdf_files)} PDFs in {category.upper()} folder.")
        
        for pdf_path in pdf_files:
            doc_name = os.path.basename(pdf_path).replace(".pdf", "")
            print(f"  📄 Parsing: {doc_name}")
            
            lines = clean_and_extract_text(pdf_path)
            articles = chunk_into_articles(lines, doc_name, category)
            all_articles.extend(articles)
            
    # Save the master articles file
    with open("output/master_articles.json", "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=4)
    print(f"\n✅ Total Articles Extracted: {len(all_articles)}")
    
    # 2. Extract Triplets with Gemini
    print("\n🧠 Starting Gemini Knowledge Graph Extraction...")
    for i, article in enumerate(all_articles):
        print(f"  [{i+1}/{len(all_articles)}] Analyzing {article['article_id']} from {article['document'][:20]}...")
        
        triplets = extract_triplets_from_article(
            article["document"], 
            article["article_id"], 
            article["text"]
        )
        
        if triplets:
            all_triplets.extend(triplets)
            
        # VERY IMPORTANT: Rate limit protection for Gemini free tier (15 requests/min)
        time.sleep(4) 
        
    # Save the master triplets file
    with open("output/master_triplets.json", "w", encoding="utf-8") as f:
        json.dump(all_triplets, f, ensure_ascii=False, indent=4)
        
    print("\n🎉 PIPELINE COMPLETE!")
    print(f"📊 Total Relationships found: {len(all_triplets)}")
    print("Files saved in the /output/ directory.")

if __name__ == "__main__":
    main()