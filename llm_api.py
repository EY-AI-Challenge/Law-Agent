import json
from openai import OpenAI
from config.settings import OPENAI_API_KEY # Importa daqui
import json
from openai import OpenAI
from config.settings import OPENAI_API_KEY # Importa daqui

client = OpenAI(api_key=OPENAI_API_KEY)


def carregar_contexto_legal():
    try:
        # Lê a base de dados (o mock_data.json que criámos)
        with open('mock_data.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
            contexto = ""
            for doc in dados['documentos']:
                contexto += f"\nLei: {doc['codigo']}, Artigo {doc['artigo']} - {doc['titulo']}\nTexto: {doc['texto']}\n"
            return contexto
    except Exception:
        return "Falha a carregar contexto. Baseia-te no Artigo 12.º do Código do Trabalho e Artigo 240.º do Código Civil."

def buscar_grafo_mock(query):
    # Isto é o que o teu Engenheiro A/B vai substituir pelo Neo4j real
    # Por agora, devolvemos a estrutura que definiste
    return {
        "nodes": [{"id": "ct", "label": "Código do Trabalho", "type": "Law"}],
        "edges": [{"from": "ct", "to": "art45", "type": "HAS_ARTICLE"}]
    }

def perguntar_ao_assistente(pergunta_utilizador):
    # 1. Recuperação do Grafo (o teu backend retorna isto)
    dados_grafo = buscar_grafo_mock(pergunta_utilizador)

    # 2. LLM (Gera apenas o texto da resposta)
    system_prompt = f"""És um consultor jurídico. Responde à questão do utilizador com base no grafo fornecido: {dados_grafo}.
    Instruções: Sê conciso, profissional e aponta riscos financeiros/legais."""

    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pergunta_utilizador}
            ],
            temperature=0.2
        )
        texto_resposta = resposta.choices[0].message.content
    except Exception as e:
        texto_resposta = f"Erro na API: {e}"

    # 3. Retorno do objeto completo (o teu JSON final)
    return {
        "answer": texto_resposta,
        "nodes": dados_grafo["nodes"],
        "edges": dados_grafo["edges"]
    }