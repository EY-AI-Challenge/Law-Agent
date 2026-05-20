import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SQLiteClient:
    """Cliente para conectar e consultar base de dados SQLite com tratamento de erros"""

    # Conecta à base de dados SQLite com validação
    def __init__(self, db_path):
        """Inicializa conexão à base de dados SQLite.
        Valida que o ficheiro existe e trata erros de conexão.
        Lança FileNotFoundError se a BD não for encontrada.
        """
        try:
            db_path = Path(db_path)
            if not db_path.exists():
                raise FileNotFoundError(f"Base de dados não encontrada: {db_path.absolute()}")
            
            logger.info(f"Conectando a SQLite: {db_path}")
            self.conn = sqlite3.connect(str(db_path))
            self.cursor = self.conn.cursor()
            logger.info("Conexão SQLite estabelecida")
        except Exception as e:
            logger.error(f"Erro ao conectar SQLite: {str(e)}")
            raise

    # Executa uma query SELECT e retorna todos os resultados
    def fetchall(self, query):
        """Executa uma query SQL e retorna todos os resultados como lista de tuplas.
        Trata erros de execução e os loga.
        """
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Erro ao executar query SQLite: {str(e)}")
            raise