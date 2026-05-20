import streamlit as st
import streamlit.components.v1 as components
import logging
from config.settings import LOG_LEVEL, LOG_FORMAT
from llm_api import perguntar_ao_assistente

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

def main() -> None:
    st.set_page_config(
        page_title="EY Legal GraphRAG",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    st.title("⚖️ Legal GraphRAG - Due Diligence Laboral")
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Análise de Risco")
        pergunta = st.text_area("Descreva a situação:", height=100)

        if st.button("Executar GraphRAG"):
            if pergunta:
                with st.spinner('A analisar dependências...'):
                    resultado = perguntar_ao_assistente(pergunta)
                    st.success("Análise Concluída")
                    st.markdown(resultado["answer"])
                    st.session_state['graph_data'] = resultado
            else:
                st.warning("Por favor, insira uma pergunta.")

    with col2:
        st.subheader("Mapeamento de Dependências Legais")
        try:
            with open("grafo_legal.html", 'r', encoding='utf-8') as f:
                html_data = f.read()
            components.html(html_data, height=550)
        except FileNotFoundError:
            st.info("Grafo não gerado. Execute o script 'gerar_grafo.py' primeiro.")

if __name__ == "__main__":
    main()