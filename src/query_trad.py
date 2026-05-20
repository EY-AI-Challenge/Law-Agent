import chromadb
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from config import GRAPH_STORE_DIR  # noqa: F401 - triggers Settings setup

chroma_client = chromadb.PersistentClient(path="chroma_db/")
chroma_collection = chroma_client.get_or_create_collection("documents")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
query_engine = index.as_query_engine()

while True:
    question = input("\nAsk a question (or 'quit' to exit): ")
    if question.lower() == "quit":
        break
    response = query_engine.query(question)
    print(f"\nAnswer: {response}")
