from pathlib import Path
from sqlite_client import SQLiteClient

BASE_DIR = Path(__file__).resolve().parent.parent
db_path = str(BASE_DIR / "data" / "data.db")

sqlite = SQLiteClient(db_path)

# Ver estrutura das tabelas
print("ESTRUTURA DAS TABELAS:\n")

tables = sqlite.fetchall("SELECT name FROM sqlite_master WHERE type='table';")
for table in tables:
    table_name = table[0]
    print(f"\n{table_name}:")
    columns = sqlite.fetchall(f"PRAGMA table_info({table_name})")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
