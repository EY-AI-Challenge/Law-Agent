from load_laws_new import KGLoader
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Resolver caminho dinamicamente baseado na localização deste ficheiro
BASE_DIR = Path(__file__).resolve().parent.parent
path_db = BASE_DIR / "data" / "data.db"

# Ponto de entrada da aplicação - cria embeddings para todas as leis
if __name__ == "__main__":
    """Script principal para criar embeddings FAISS das leis.
    Carrega leis do mock.db, cria embeddings com sentence-transformers,
    e guarda índice FAISS para buscas rápidas.
    """
    try:
        logger.info(f"Iniciando carregamento de dados. BD: {path_db}")
        loader = KGLoader(str(path_db))
        loader.run()
        logger.info("Carregamento concluído com sucesso!")
    except Exception as e:
        logger.error(f"Erro durante carregamento: {str(e)}", exc_info=True)