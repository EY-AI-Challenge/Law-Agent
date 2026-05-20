import os
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.huggingface_api import HuggingFaceInferenceAPI

load_dotenv()

GRAPH_STORE_DIR = "graph_store/"
CIVIL_GRAPH_STORE_DIR = "graph_store/civil/"
LABOUR_GRAPH_STORE_DIR = "graph_store/labour/"

Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.chunk_size = 512
Settings.chunk_overlap = 50

Settings.llm = HuggingFaceInferenceAPI(
    model_name="Qwen/Qwen2.5-72B-Instruct",
    token=os.getenv("HF_TOKEN"),
)
