import asyncio
import os
from dotenv import load_dotenv
from llama_index.core import Settings, StorageContext, load_index_from_storage
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import FunctionAgent
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.huggingface_api import HuggingFaceInferenceAPI

load_dotenv()

CIVIL_GRAPH_STORE_DIR = "graph_store/civil/"
LABOUR_GRAPH_STORE_DIR = "graph_store/labour/"

Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.chunk_size = 512
Settings.chunk_overlap = 50


async def main():
    llm = HuggingFaceInferenceAPI(
        model_name="Qwen/Qwen2.5-72B-Instruct",
        token=os.getenv("HF_TOKEN"),
        streaming=False,
    )
    Settings.llm = llm

    civil_index = load_index_from_storage(
        StorageContext.from_defaults(persist_dir=CIVIL_GRAPH_STORE_DIR)
    )
    labour_index = load_index_from_storage(
        StorageContext.from_defaults(persist_dir=LABOUR_GRAPH_STORE_DIR)
    )

    civil_tool = QueryEngineTool(
        query_engine=civil_index.as_query_engine(include_text=True),
        metadata=ToolMetadata(
            name="civil_law_search",
            description=(
                "Search the civil law knowledge base. Use for questions about civil legislation, "
                "civil rights, contracts, property, obligations, and related civil law documents."
            ),
        ),
    )

    labour_tool = QueryEngineTool(
        query_engine=labour_index.as_query_engine(include_text=True),
        metadata=ToolMetadata(
            name="labour_law_search",
            description=(
                "Search the labour law knowledge base. Use for questions about employment, "
                "workers' rights, labour contracts, workplace regulations, and related labour law documents."
            ),
        ),
    )

    agent = FunctionAgent(
        name="document_agent",
        tools=[civil_tool, labour_tool],
        llm=llm,
        verbose=True,
    )

    while True:
        question = input("\nAsk a question (or 'quit' to exit): ")
        if question.lower() == "quit":
            break
        response = await agent.run(question)
        print(f"\nAnswer: {response}")


asyncio.run(main())
