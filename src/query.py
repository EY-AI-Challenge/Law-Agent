from llama_index.core import StorageContext, load_index_from_storage
from config import GRAPH_STORE_DIR

storage_context = StorageContext.from_defaults(persist_dir=GRAPH_STORE_DIR)
index = load_index_from_storage(storage_context)

query_engine = index.as_query_engine(include_text=True)

while True:
    question = input("\nAsk a question (or 'quit' to exit): ")
    if question.lower() == "quit":
        break
    response = query_engine.query(question)
    print(f"\nAnswer: {response}")
