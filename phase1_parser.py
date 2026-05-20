import fitz  # PyMuPDF
import json
import os

def clean_and_extract_text(pdf_path):
    """
    Extracts text from the PDF and cleans up repetitive footers/headers.
    """
    doc = fitz.open(pdf_path)
    clean_lines = []
    
    for page in doc:
        text = page.get_text("text")
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and Diário da República footers/headers
            if not line:
                continue
            if line == "LEGISLAÇÃO CONSOLIDADA":
                continue
            if line.startswith("Versão à data de") or "Pág." in line:
                continue
            # Skip the Imprensa Nacional Casa da Moeda footer
            if line == "IMPRENSA NACIONAL CASA DA MOEDA":
                continue
                
            clean_lines.append(line)
            
    return clean_lines

def chunk_into_articles(clean_lines, document_name):
    """
    Chunks lines into Articles. Uses a Dictionary to automatically overwrite 
    the 'Index' entries with the actual 'Body' entries!
    """
    articles_dict = {} 
    
    current_article_id = None
    current_article_title = None
    current_article_text = []
    
    for i, line in enumerate(clean_lines):
        
        # Hackathon logic: An article header starts with "Artigo", contains "º", and is short.
        # This catches "Artigo 1.º" and "Artigo 91.º-A" while ignoring normal sentences.
        is_exact_article_header = line.startswith("Artigo ") and "º" in line and len(line) < 20
        
        if is_exact_article_header:
            # Save the previous article before starting the new one
            if current_article_id:
                articles_dict[current_article_id] = {
                    "document": document_name,
                    "article_id": current_article_id,
                    "title": current_article_title,
                    "text": "\n".join(current_article_text).strip()
                }
            
            # Start tracking the new article
            current_article_id = line
            current_article_title = clean_lines[i + 1] if i + 1 < len(clean_lines) else "Sem Título"
            current_article_text = []
            
        else:
            # We are inside the body of an article
            if current_article_id and line != current_article_title:
                current_article_text.append(line)
                
    # Don't forget to save the very last article in the document!
    if current_article_id:
        articles_dict[current_article_id] = {
            "document": document_name,
            "article_id": current_article_id,
            "title": current_article_title,
            "text": "\n".join(current_article_text).strip()
        }
        
    # Convert the dictionary back to a clean list
    return list(articles_dict.values())

def process_pdf(pdf_path):
    # Extract document name from the file name
    document_name = os.path.basename(pdf_path).replace(".pdf", "")
    
    # Run the pipeline
    lines = clean_and_extract_text(pdf_path)
    articles_data = chunk_into_articles(lines, document_name)
    
    return articles_data

if __name__ == "__main__":
    # TEST WORKFLOW:
    # 1. Put one of your downloaded PDFs in the same folder.
    # 2. Change the filename below to match your PDF.
    
    test_pdf = "Consolidação Decreto-Lei n.º 259_2009  - Diário da República n.º 187_2009, Série I de 2009-09-25.pdf" # <-- CHANGE THIS to one of your PDF filenames
    
    try:
        results = process_pdf(test_pdf)
        
        # Save to JSON to easily inspect the data
        output_file = f"{test_pdf}_parsed.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Success! Extracted {len(results)} articles.")
        print(f"📄 Check the '{output_file}' file to see the structured data.")
        
        # Print a quick preview of the first article
        if results:
            print("\n--- PREVIEW OF FIRST ARTICLE ---")
            print(f"Doc: {results[0]['document']}")
            print(f"Art: {results[0]['article_id']} - {results[0]['title']}")
            print(f"Text Preview: {results[0]['text'][:150]}...\n")
            
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")