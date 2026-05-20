"""
Script simples para testar queries no KG
"""
from pathlib import Path
from sqlite_client import SQLiteClient

# Configuração
BASE_DIR = Path(__file__).resolve().parent.parent
db_path = str(BASE_DIR / "data" / "data.db")

# Conectar à base de dados
sqlite = SQLiteClient(db_path)

print("\n" + "="*60)
print("TESTE 1: Listar todas as leis")
print("="*60)

laws = sqlite.fetchall("SELECT id, tipo, numero, emissor, data_publicacao FROM legislacao LIMIT 5")
for law in laws:
    print(f"ID: {law[0]}, Tipo: {law[1]} {law[2]}, Emissor: {law[3]}, Data: {law[4]}")

print("\n" + "="*60)
print("TESTE 2: Buscar leis por emissor")
print("="*60)

laws_by_issuer = sqlite.fetchall("SELECT tipo, numero, emissor, texto_sumario FROM legislacao WHERE emissor LIKE '%Assembleia%' LIMIT 3")
for law in laws_by_issuer:
    print(f"Lei: {law[0]} {law[1]} | Emissor: {law[2]}")
    print(f"Sumário: {law[3]}\n")

print("\n" + "="*60)
print("TESTE 3: Listar temas únicos")
print("="*60)

themes = sqlite.fetchall("SELECT DISTINCT nome FROM tema LIMIT 10")
for theme in themes:
    print(f"- {theme[0]}")

print("\n" + "="*60)
print("TESTE 4: Leis por tema")
print("="*60)

laws_by_theme = sqlite.fetchall("""
    SELECT l.tipo, l.numero, l.emissor, l.texto_sumario, t.nome
    FROM legislacao l
    JOIN legislacao_tema lt ON l.id = lt.legislacao_id
    JOIN tema t ON lt.tema_id = t.id
    LIMIT 5
""")
for law in laws_by_theme:
    print(f"Lei: {law[0]} {law[1]} | Emissor: {law[2]} | Tema: {law[4]}")
    print(f"Sumário: {law[3]}\n")

print("\n" + "="*60)
print("TESTE 5: Referências entre leis")
print("="*60)

refs = sqlite.fetchall("""
    SELECT l1.tipo, l1.numero, l2.tipo, l2.numero, ref.tipo_relacao
    FROM legislacao_referencia ref
    JOIN legislacao l1 ON ref.origem_id = l1.id
    LEFT JOIN legislacao l2 ON ref.destino_id = l2.id
    LIMIT 5
""")
for ref in refs:
    print(f"{ref[0]} {ref[1]} →({ref[4]})→ {ref[2]} {ref[3]}")
