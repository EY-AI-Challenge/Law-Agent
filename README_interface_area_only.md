# Legal Network Agent — filtros só por área

Interface Streamlit baseada em ChromaDB para explorar a rede de citações legais.

## Como correr

```bash
pip install -r requirements_ui.txt
streamlit run app_graph_chromadb.py
```

## Notas

- O grafo usa apenas filtro por área jurídica.
- As cores dos nós representam áreas jurídicas/temas.
- Foram removidos os filtros de peso e tipo de relação da interface.
- A app usa a coleção ChromaDB `dre_legislacao_em_vigor` por defeito.
