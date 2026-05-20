from sqlite_client import SQLiteClient
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
try:
    import faiss
except ImportError:
    faiss = None

logger = logging.getLogger(__name__)

class KGLoader:
    """Carrega leis da base de dados SQLite e cria embeddings com índice FAISS"""

    # Inicializa o loader com acesso a SQLite e modelo de embeddings
    def __init__(self, sqlite_path):
        """Inicializa KGLoader.
        Conecta à base de dados SQLite e carrega o modelo de embeddings.
        Define o diretório base para guardar os ficheiros gerados.
        """
        try:
            logger.info("Inicializando KGLoader...")
            self.sqlite = SQLiteClient(sqlite_path)
            self.model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            self.base_dir = Path(sqlite_path).parent.parent
            logger.info("KGLoader inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar KGLoader: {str(e)}")
            raise

    # Carrega leis do SQLite e cria embeddings FAISS
    def create_embeddings(self):
        """Cria embeddings para todas as leis com sumário.
        Processa textos das leis através do modelo de embeddings multilíngue.
        Cria índice FAISS e guarda ficheiros: faiss_index.bin e law_ids.pkl.
        """
        try:
            logger.info("Recuperando leis da base de dados...")
            laws = self.sqlite.fetchall("""
                SELECT id, texto_sumario, tipo, numero
                FROM legislacao
                WHERE texto_sumario IS NOT NULL
            """)

            if not laws:
                logger.warning("Nenhuma lei encontrada com sumário")
                return

            logger.info(f"Encontradas {len(laws)} leis")

            # Preparar textos
            texts = []
            law_ids = []
            for law_id, summary, tipo, numero in laws:
                text = f"{tipo} {numero}: {summary}"
                texts.append(text)
                law_ids.append(law_id)

            # Criar embeddings
            logger.info("Criando embeddings...")
            embeddings = self.model.encode(texts, show_progress_bar=True).astype('float32')
            logger.info(f"Embeddings criados: {embeddings.shape}")

            # Criar índice FAISS
            if faiss is not None:
                logger.info("Criando índice FAISS...")
                dimension = embeddings.shape[1]
                index = faiss.IndexFlatL2(dimension)
                index.add(embeddings)

                # Guardar
                embedding_path = self.base_dir / "data" / "faiss_index.bin"
                embedding_path.parent.mkdir(parents=True, exist_ok=True)
                faiss.write_index(index, str(embedding_path))
                
                # Guardar IDs
                import pickle
                ids_path = self.base_dir / "data" / "law_ids.pkl"
                with open(ids_path, 'wb') as f:
                    pickle.dump(law_ids, f)
                logger.info(f"Índice guardado em {embedding_path}")
            else:
                logger.warning("FAISS não instalado")
        except Exception as e:
            logger.error(f"Erro ao criar embeddings: {str(e)}")
            raise

    # Executa o pipeline completo de carregamento
    def run(self):
        """Executa o pipeline completo de carregamento e criação de embeddings.
        Chama create_embeddings() para processar todas as leis.
        """
        print("Creating embeddings...")
        self.create_embeddings()
        print("DONE")
