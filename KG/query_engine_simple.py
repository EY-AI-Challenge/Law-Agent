import logging
from sqlite_client import SQLiteClient
from pathlib import Path
import pickle

try:
    import faiss
except ImportError:
    faiss = None

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class QueryEngine:
    """Motor de queries para buscar leis usando embeddings FAISS e SQLite"""

    # Inicializa o motor de queries com acesso a SQLite, modelo de embeddings e índice FAISS
    def __init__(self, sqlite_path):
        """Inicializa o QueryEngine com caminho à base de dados SQLite.
        Carrega o modelo de embeddings e tenta carregear o índice FAISS.
        """
        self.sqlite = SQLiteClient(sqlite_path)
        self.model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.base_dir = Path(sqlite_path).parent.parent
        
        self.index = None
        self.law_ids = []
        self.load_embeddings_index()

    # Carrega o índice FAISS guardado em disco
    def load_embeddings_index(self):
        """Carrega o índice FAISS do ficheiro faiss_index.bin.
        Também carrega os IDs correspondentes das leis de law_ids.pkl.
        Retorna True se bem-sucedido, False caso contrário.
        """
        if faiss is None:
            logger.warning("FAISS não instalado")
            return False

        embedding_path = self.base_dir / "data" / "faiss_index.bin"
        ids_path = self.base_dir / "data" / "law_ids.pkl"

        if not embedding_path.exists():
            logger.warning("Índice FAISS não encontrado. Execute load_laws_new.py primeiro")
            return False

        try:
            logger.info("Carregando índice FAISS...")
            self.index = faiss.read_index(str(embedding_path))
            with open(ids_path, 'rb') as f:
                self.law_ids = pickle.load(f)
            logger.info(f"Índice carregado com {len(self.law_ids)} leis")
            return True
        except Exception as e:
            logger.error(f"Erro ao carregar índice: {str(e)}")
            return False

    # Busca leis por similaridade semântica usando embeddings
    def search_by_semantic(self, query, top_k=5):
        """Busca leis por similaridade semântica.
        Converte a query em embedding e procura as top_k leis mais similares no índice FAISS.
        Retorna lista de dicionários com lei_id, score, tipo, número, data, etc.
        """
        if self.index is None:
            logger.error("Índice não carregado")
            return []

        try:
            logger.info(f"Busca semântica: '{query}'")
            query_embedding = self.model.encode([query]).astype('float32')
            distances, indices = self.index.search(query_embedding, top_k)

            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.law_ids):
                    law_id = self.law_ids[idx]
                    score = float(1 / (1 + distances[0][i]))
                    
                    # Obter detalhes
                    law_detail = self.get_law_details(law_id)
                    if law_detail:
                        results.append({
                            "law_id": law_id,
                            "score": score,
                            "tipo": law_detail[0],
                            "numero": law_detail[1],
                            "data": law_detail[2],
                            "emissor": law_detail[3],
                            "sumario": law_detail[4][:200] + "..." if law_detail[4] else "",
                            "url": law_detail[5]
                        })

            logger.info(f"Encontradas {len(results)} leis similares")
            return results

        except Exception as e:
            logger.error(f"Erro ao buscar: {str(e)}")
            return []

    # Busca leis filtrando por tópico/categoria
    def search_by_topic(self, topic_name, max_results=10):
        """Busca leis filtrando por nome de tópico.
        Faz uma query SQL na tabela legislacao_tema.
        Retorna lista de leis com tópico correspondente (até max_results).
        """
        logger.info(f"Busca por tópico: '{topic_name}'")

        try:
            results = self.sqlite.fetchall(f"""
                SELECT DISTINCT l.id, l.tipo, l.numero, l.data_publicacao, 
                       l.emissor, t.nome
                FROM legislacao l
                JOIN legislacao_tema lt ON l.id = lt.legislacao_id
                JOIN tema t ON lt.tema_id = t.id
                WHERE LOWER(t.nome) LIKE LOWER('%{topic_name}%')
                LIMIT {max_results}
            """)
            
            return [
                {
                    "law_id": r[0],
                    "tipo": r[1],
                    "numero": r[2],
                    "data": r[3],
                    "emissor": r[4],
                    "topic": r[5]
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Erro na busca por tópico: {str(e)}")
            return []

    # Busca leis relacionadas através de referências (alterações, revogações, etc)
    def search_by_references(self, law_id, max_depth=2):
        """Busca leis relacionadas por referências.
        Procura na tabela legislacao_referencia leis que citam ou são citadas por law_id.
        Retorna lista de leis relacionadas com tipo de relação.
        """
        logger.info(f"Busca de referências para lei {law_id}")

        try:
            results = self.sqlite.fetchall(f"""
                SELECT DISTINCT l2.id, l2.tipo, l2.numero, lr.tipo_relacao
                FROM legislacao_referencia lr
                JOIN legislacao l1 ON lr.origem_id = l1.id
                JOIN legislacao l2 ON lr.destino_id = l2.id
                WHERE lr.origem_id = {law_id} OR lr.destino_id = {law_id}
            """)
            
            return [
                {
                    "law_id": r[0],
                    "tipo": r[1],
                    "numero": r[2],
                    "relacao": r[3]
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Erro na busca de referências: {str(e)}")
            return []

    # Retorna informações completas sobre uma lei específica
    def get_law_details(self, law_id):
        """Obtém detalhes completos de uma lei pelo ID.
        Retorna tupla com (tipo, numero, data, emissor, sumario, url) ou None se não encontrada.
        """
        try:
            result = self.sqlite.fetchall(f"""
                SELECT tipo, numero, data_publicacao, emissor, texto_sumario, url
                FROM legislacao
                WHERE id = {law_id}
            """)
            if result:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Erro ao obter detalhes: {str(e)}")
            return None

    # Fecha as conexões (placeholder para futuras melhorias)
    def close(self):
        """Fecha as conexões e liberta recursos.
        Placeholder para futuras implementações de cleanup.
        """
        pass
