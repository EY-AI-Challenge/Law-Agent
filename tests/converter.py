import os
import re
import sqlite3
from pathlib import Path

# Verifica se a biblioteca pypdf está instalada
try:
    import pypdf
except ImportError:
    print("A biblioteca 'pypdf' é necessária. Instale-a rodando: pip install pypdf")
    exit(1)

DB_NAME = "data.db"
BASE_DIR = Path("Arquivos")

def inicializar_banco():
    """Cria a estrutura de tabelas no banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Ativar suporte a chaves estrangeiras
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. TABELA PRINCIPAL
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS legislacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dre_id TEXT UNIQUE NOT NULL,
        tipo TEXT NOT NULL,
        numero TEXT,
        data_publicacao TEXT,
        emissor TEXT,
        estado TEXT,
        url TEXT,
        texto_sumario TEXT,
        caminho_pdf TEXT
    );
    """)
    
    # 2. TABELA DE TEMAS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tema (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL
    );
    """)
    
    # 3. TABELA PIVÔ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS legislacao_tema (
        legislacao_id INTEGER,
        tema_id INTEGER,
        PRIMARY KEY (legislacao_id, tema_id),
        FOREIGN KEY (legislacao_id) REFERENCES legislacao(id) ON DELETE CASCADE,
        FOREIGN KEY (tema_id) REFERENCES tema(id) ON DELETE CASCADE
    );
    """)
    
    # 4. TABELA DE REFERÊNCIAS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS legislacao_referencia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origem_id INTEGER NOT NULL,
        destino_texto TEXT NOT NULL,
        destino_id INTEGER DEFAULT NULL,
        tipo_relacao TEXT,
        FOREIGN KEY (origem_id) REFERENCES legislacao(id) ON DELETE CASCADE,
        FOREIGN KEY (destino_id) REFERENCES legislacao(id) ON DELETE SET NULL
    );
    """)
    
    conn.commit()
    conn.close()

def parse_filename(filename):
    """Extrai tipo, número e data de publicação a partir do nome do arquivo."""
    # Exemplo de correspondência: Consolidação Decreto-Lei n.º 78_2026 - Diário... de 2026-03-16.pdf
    type_num_match = re.search(r"Consolidação\s+([\w\-]+(?:-[\w\-]+)?)\s+n\.º\s+([\w\-\./]+)", filename)
    tipo = type_num_match.group(1).strip() if type_num_match else "Desconhecido"
    numero_raw = type_num_match.group(2).strip() if type_num_match else "Desconhecido"
    
    # Normalizar o número substituindo underscores por barras
    numero = numero_raw.replace('_', '/')
    
    # Extrair data de publicação YYYY-MM-DD no final do nome do arquivo
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    data_pub = date_match.group(1) if date_match else None
    
    return tipo, numero, data_pub

def extrair_texto_pdf(filepath):
    """Extrai e retorna todo o texto contido no arquivo PDF."""
    texto = ""
    try:
        reader = pypdf.PdfReader(filepath)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                texto += page_text + "\n"
    except Exception as e:
        print(f"Erro ao ler o arquivo {filepath}: {e}")
    return texto

def extrair_sumario(texto, tipo, numero):
    """Usa expressões regulares para identificar o resumo principal da lei."""
    # Padrão para capturar texto logo após a identificação da portaria/lei até ao preâmbulo do governo
    pattern = rf"(?:{tipo}\s+n\.º\s+{re.escape(numero)}|{tipo}\s+n\.º\s+{re.escape(numero.replace('/', '_'))})\s*\n\s*de\s+\d+\s+de\s+\w+\s*\n\s*(.*?)(?=\n\s*[O|A]\s+programa|\n\s*Nos\s+termos|\n\s*Artigo|\Z)"
    match = re.search(pattern, texto, re.DOTALL | re.IGNORECASE)
    if match:
        return re.sub(r'\s+', ' ', match.group(1).strip())
    
    # Fallback simples caso não encontre o padrão exato
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    for i, linha in enumerate(linhas):
        if "de março" in linha.lower() or "de abril" in linha.lower() or "de de" in linha.lower():
            if i + 1 < len(linhas):
                return linhas[i+1]
    return "Sumário não disponível."

def identificar_referencias(texto, tipo_atual, numero_atual):
    """Procura referências a diplomas legais no texto e tenta deduzir a relação."""
    referencias = []
    
    # Capturar menções a diplomas do tipo: Decreto-Lei n.º X/Y, Portaria n.º X/Y ou Lei n.º X/Y
    ref_pattern = re.compile(r"((?:Decreto-Lei|Lei|Portaria|Declaração de Retificação)\s+n\.º\s+[\d\w\-C/]+)", re.IGNORECASE)
    matches = ref_pattern.findall(texto)
    
    # Determinar contexto de revogação próximo
    linhas = texto.split('\n')
    
    for match in set(matches):
        ref_norm = match.strip().replace('_', '/')
        # Evitar auto-referência
        if numero_atual in ref_norm and tipo_atual.lower() in ref_norm.lower():
            continue
            
        tipo_relacao = "Menciona"
        
        # Heurística para classificar relação
        for linha in linhas:
            if match in linha:
                linha_lc = linha.lower()
                if "alterado" in linha_lc or "alteração" in linha_lc or "introduzidas por" in linha_lc:
                    tipo_relacao = "Altera"
                    break
                elif "revogado" in linha_lc or "revogatória" in linha_lc or "cessa" in linha_lc:
                    tipo_relacao = "Revoga"
                    break
                elif "regulamenta" in linha_lc or "ao abrigo" in linha_lc:
                    tipo_relacao = "Regulamenta"
                    break
                    
        referencias.append((ref_norm, tipo_relacao))
        
    return referencias

def processar_arquivos():
    """Varre a pasta 'Arquivos', extrai dados e armazena no SQLite."""
    if not BASE_DIR.exists():
        print(f"Diretório base '{BASE_DIR}' não encontrado.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print("Iniciando processamento dos arquivos PDF...")

    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith(".pdf"):
                filepath = Path(root) / file
                tema_nome = filepath.parent.name.capitalize() # Nome da pasta vira o Tema
                
                print(f"Processando: {filepath.relative_to(BASE_DIR)}")
                
                # 1. Obter metadados do nome do arquivo
                tipo, numero, data_pub = parse_filename(file)
                dre_id = f"{tipo.lower()}_{numero.replace('/', '_')}"
                
                # 2. Extrair texto completo do PDF
                texto_pdf = extrair_texto_pdf(filepath)
                
                # 3. Determinar Estado da lei
                estado = "Em vigor"
                if "alterações introduzidas por" in texto_pdf.lower():
                    estado = "Alterado"
                elif "revogado" in texto_pdf.lower() and "norma revogatória" in texto_pdf.lower():
                    estado = "Revogado"
                
                # 4. Extrair sumário limpo
                texto_sumario = extrair_sumario(texto_pdf, tipo, numero)
                
                # 5. Emissor genérico (Pode ser refinado se necessário)
                emissor = "Governo da República Portuguesa"
                url_mock = f"https://diariodarepublica.pt/dr/detalhe/{tipo.lower()}/{numero.replace('/', '-')}"
                
                # Salvar Tema na base de dados
                cursor.execute("INSERT OR IGNORE INTO tema (nome) VALUES (?)", (tema_nome,))
                cursor.execute("SELECT id FROM tema WHERE nome = ?", (tema_nome,))
                tema_id = cursor.fetchone()[0]
                
                # Salvar Legislação
                try:
                    cursor.execute("""
                    INSERT INTO legislacao (dre_id, tipo, numero, data_publicacao, emissor, estado, url, texto_sumario, caminho_pdf)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (dre_id, tipo, numero, data_pub, emissor, estado, url_mock, texto_sumario, str(filepath)))
                    legislacao_id = cursor.lastrowid
                except sqlite3.IntegrityError:
                    # Se já existir, obter ID existente
                    cursor.execute("SELECT id FROM legislacao WHERE dre_id = ?", (dre_id,))
                    legislacao_id = cursor.fetchone()[0]
                
                # Vincular Legislação ao Tema
                cursor.execute("INSERT OR IGNORE INTO legislacao_tema (legislacao_id, tema_id) VALUES (?, ?)", (legislacao_id, tema_id))
                
                # Identificar e Salvar referências encontradas
                referencias = identificar_referencias(texto_pdf, tipo, numero)
                for destino_texto, tipo_relacao in referencias:
                    cursor.execute("""
                    INSERT INTO legislacao_referencia (origem_id, destino_texto, tipo_relacao)
                    VALUES (?, ?, ?)
                    """, (legislacao_id, destino_texto, tipo_relacao))

    conn.commit()
    
    # 6. RESOLUÇÃO DOS IDs DE DESTINO DAS REFERÊNCIAS
    print("Atualizando chaves estrangeiras das referências identificadas...")
    cursor.execute("SELECT id, destino_texto FROM legislacao_referencia")
    referencias_db = cursor.fetchall()
    
    for ref_id, destino_texto in referencias_db:
        # Tenta casar o destino_texto com uma lei que importamos
        cursor.execute("SELECT id FROM legislacao")
        leis = cursor.fetchall()
        for lei_id in leis:
            cursor.execute("SELECT tipo, numero FROM legislacao WHERE id = ?", (lei_id[0],))
            tipo_l, numero_l = cursor.fetchone()
            # Se o texto de referência contiver as informações estruturadas da lei alvo
            if tipo_l.lower() in destino_texto.lower() and numero_l.lower() in destino_texto.lower():
                cursor.execute("UPDATE legislacao_referencia SET destino_id = ? WHERE id = ?", (lei_id[0], ref_id))
                break

    conn.commit()
    conn.close()
    print(f"Sucesso! O banco de dados '{DB_NAME}' foi gerado e preenchido.")

if __name__ == "__main__":
    inicializar_banco()
    processar_arquivos()
