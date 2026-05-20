from pathlib import Path
from sqlite_client import SQLiteClient

base_dir = Path(__file__).resolve().parent.parent
sqlite = SQLiteClient(str(base_dir / 'data' / 'mock.db'))

# Contar registos
print(sqlite.fetchall("SELECT COUNT(*) FROM legislacao")[0])
print(sqlite.fetchall("SELECT COUNT(*) FROM legislacao_tema")[0])
print(sqlite.fetchall("SELECT COUNT(*) FROM legislacao_referencia")[0])