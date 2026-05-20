from google import genai
from google.genai import types
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini
# It will automatically look for the GEMINI_API_KEY environment variable
client = genai.Client()

def extract_triplets_from_article(document_name, article_id, text):
    """
    Asks Gemini to extract legal references from the text and return them as a JSON array.
    """
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
            config=types.GenerateContentConfig(temperature=0.1) # Low temperature for factual extraction
        )
        
        raw_text = response.text.strip()
        
        # Clean up Markdown if Gemini accidentally adds it
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()
            
        triplets = json.loads(raw_text)
        return triplets
        
    except Exception as e:
        print(f"  [!] Failed to extract triplets for {article_id}: {e}")
        return []

def process_parsed_json(json_path):
    """
    Reads a parsed JSON file, extracts triplets for each article, and saves the result.
    """
    print(f"Processing {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)
        
    all_triplets = []
    
    # For testing purposes, let's just process the first 15 articles to see if it works
    # Change `articles[:15]` to `articles` to run the full document later
    for i, article in enumerate(articles[:10]): 
        print(f"  Analyzing {article['article_id']} ({i+1}/15)...")
        
        triplets = extract_triplets_from_article(
            article["document"], 
            article["article_id"], 
            article["text"]
        )
        
        if triplets:
            all_triplets.extend(triplets)
            for t in triplets:
                print(f"    -> FOUND: [{t['source']}] --{t['relationship']}--> [{t['target']}]")
                
        # Pause to avoid Gemini free-tier rate limits (15 requests per minute)
        time.sleep(3) 
        
    # Save the output
    output_path = json_path.replace("_parsed.json", "_triplets.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_triplets, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Finished! Extracted {len(all_triplets)} total relationships.")
    print(f"📄 Saved to {output_path}")

if __name__ == "__main__":
    # TEST WORKFLOW:
    # Point this to the JSON file you just generated in Phase 1!
    test_json_file = "Consolidação Decreto-Lei n.º 259_2009  - Diário da República n.º 187_2009, Série I de 2009-09-25.pdf_parsed.json"
    
    process_parsed_json(test_json_file)