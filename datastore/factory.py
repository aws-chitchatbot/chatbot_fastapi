from datastore.datastore import DataStore
import os
import setting.setting


async def get_datastore() -> DataStore:
    datastore = os.environ.get("DATASTORE")
    assert datastore is not None

    match datastore:
        case "pinecone":
            from datastore.providers.pinecone_datastore import PineconeDataStore

            return PineconeDataStore()
        case "elasticsearch":
            from datastore.providers.elasticsearch_datastore import (
                ElasticsearchDataStore,
            )

            return ElasticsearchDataStore()
        case _:
            raise ValueError(
                f"Unsupported vector database: {datastore}. "
                f"Try one of the following: llama, elasticsearch, pinecone, weaviate, milvus, zilliz, redis, azuresearch, or qdrant"
            )
