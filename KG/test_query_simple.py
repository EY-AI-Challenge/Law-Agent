"""
Script de testes para demonstrar o uso do QueryEngine.
Exemplos práticos das 3 tipos de busca: semântica, por tópico e por referências.
"""
import logging
from pathlib import Path
from query_engine_simple import QueryEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Função principal que demonstra os 3 tipos de queries disponíveis."""
    # Configuração
    BASE_DIR = Path(__file__).resolve().parent.parent
    sqlite_path = str(BASE_DIR / "data" / "mock.db")

    try:
        # Inicializar engine
        logger.info("Inicializando QueryEngine...")
        engine = QueryEngine(sqlite_path)

        # ========================================
        # 1. BUSCA SEMÂNTICA (embeddings)
        # ========================================
        print("\n" + "="*60)
        print("BUSCA SEMÂNTICA - Leis sobre trabalho")
        print("="*60)
        
        semantic_results = engine.search_by_semantic("trabalho direitos laborais contrato", top_k=5)
        for i, result in enumerate(semantic_results, 1):
            print(f"\n{i}. Score: {result['score']:.4f}")
            print(f"   Lei: {result['tipo']} {result['numero']}")
            print(f"   Emitente: {result['emissor']}")
            print(f"   Data: {result['data']}")
            print(f"   Sumário: {result['sumario']}")

        # ========================================
        # 2. BUSCA POR TÓPICO
        # ========================================
        print("\n" + "="*60)
        print("BUSCA POR TÓPICO")
        print("="*60)
        
        topic_results = engine.search_by_topic("trabalho", max_results=5)
        if topic_results:
            for result in topic_results[:5]:
                print(f"\nLei: {result['tipo']} {result['numero']}")
                print(f"Tópico: {result['topic']}")
        else:
            print("Nenhum resultado encontrado")

        # ========================================
        # 3. BUSCAR REFERÊNCIAS NO GRAFO
        # ========================================
        print("\n" + "="*60)
        print("BUSCAR REFERÊNCIAS")
        print("="*60)
        
        if semantic_results:
            law_id = semantic_results[0]['law_id']
            print(f"\nBuscando referências para lei ID: {law_id}")
            
            ref_results = engine.search_by_references(law_id)
            if ref_results:
                print(f"Encontradas {len(ref_results)} referências")
                for result in ref_results[:5]:
                    print(f"  - Lei {result['law_id']}: {result['tipo']} {result['numero']}")
                    print(f"    Relação: {result['relacao']}")
            else:
                print("Nenhuma referência encontrada")

        engine.close()
        logger.info("Concluído!")

    except Exception as e:
        logger.error(f"Erro: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
