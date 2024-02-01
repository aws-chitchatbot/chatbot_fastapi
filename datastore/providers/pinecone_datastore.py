import os
from typing import Any, Dict, List, Optional
import pinecone
from tenacity import retry, wait_random_exponential, stop_after_attempt
import asyncio
from loguru import logger

from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    Source,
)
from services.date import to_unix_timestamp

# Pinecone 설정을 위한 환경 변수 읽기
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT")
PINECONE_INDEX = os.environ.get("PINECONE_INDEX")
assert PINECONE_API_KEY is not None
assert PINECONE_ENVIRONMENT is not None
assert PINECONE_INDEX is not None

# API 키와 환경으로 Pinecone 초기화
pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)

# 벡터 업서트의 배치 크기를 Pinecone으로 설정
UPSERT_BATCH_SIZE = 5


class PineconeDataStore(DataStore):
    def __init__(self):
        # 인덱스 이름이 지정되어 있고 Pinecone에 존재하는지 확인
        if PINECONE_INDEX and PINECONE_INDEX not in pinecone.list_indexes():
            # 메타데이터 객체의 모든 필드를 목록으로 가져오기
            fields_to_index = list(DocumentChunkMetadata.__fields__.keys())

            # 특정 인덱스가 없을경우, 지정된 이름, 차원 및 메타데이터 구성으로 새 인덱스를 만든다
            try:
                logger.info(f"인덱스 {PINECONE_INDEX} 이하와 같은 {fields_to_index}로 생성")
                pinecone.create_index(
                    PINECONE_INDEX,
                    dimension=768,  # Gemini models/embedding-001 임베딩의 차원
                    metadata_config={"indexed": fields_to_index},
                )
                self.index = pinecone.Index(PINECONE_INDEX)
                logger.info(f"Index {PINECONE_INDEX} created successfully")
            except Exception as e:
                logger.error(f"Error creating index {PINECONE_INDEX}: {e}")
                raise e
        elif PINECONE_INDEX and PINECONE_INDEX in pinecone.list_indexes():
            # 특정 인덱스가 있을 경우
            try:
                logger.info(f" {PINECONE_INDEX} 인덱스에 연결중...")
                self.index = pinecone.Index(PINECONE_INDEX)
                logger.info(f"인덱스 {PINECONE_INDEX}에 성공적으로 연결")
            except Exception as e:
                logger.error(f"인덱스 {PINECONE_INDEX}에 연결하는데 실패함: {e}")
                raise e

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        document ID에서 document 청크의 목록으로 딕셔너리를 받아 인덱스에 삽입
        document ID 목록을 반환합니다.
        """
        # 반환할 ID 목록 초기화
        doc_ids: List[str] = []
        # upsert 할 벡터 목록을 초기화
        vectors = []
        for doc_id, chunk_list in chunks.items():
            # 아이디 목록에 아이디를 추가
            doc_ids.append(doc_id)
            logger.info(f"Upserting document_id: {doc_id}")
            for chunk in chunk_list:
                # (아이디, 임베딩, 메타데이터)의 벡터 튜플을 생성
                # 날짜에 대한 Unix 타임스탬프가 있는 딕셔너리로 메타데이터 객체를 변환
                pinecone_metadata = self._get_pinecone_metadata(chunk.metadata)
                # 메타데이터 딕셔너리에 텍스트와 문서 ID를 추가
                pinecone_metadata["text"] = chunk.text
                pinecone_metadata["document_id"] = doc_id
                vector = (chunk.id, chunk.embedding, pinecone_metadata)
                vectors.append(vector)
        # 벡터 목록을 지정된 크기의 배치로 분할
        batches = [
            vectors[i : i + UPSERT_BATCH_SIZE]
            for i in range(0, len(vectors), UPSERT_BATCH_SIZE)
        ]
        for batch in batches:
            try:
                logger.info(f"Upserting batch of size {len(batch)}")
                self.index.upsert(vectors=batch)
                logger.info(f"Upserted batch successfully")
            except Exception as e:
                logger.error(f"Error upserting batch: {e}")
                raise e

        return doc_ids

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """
        임베딩 및 필터가 포함된 쿼리 목록을 받아 일치하는 문서 청크 및 점수가 포함된 쿼리 결과 목록을 반환
        """

        # Define a helper coroutine that performs a single query and returns a QueryResult
        async def _single_query(query: QueryWithEmbedding) -> QueryResult:
            logger.debug(f"Query: {query.query}")

            # Convert the metadata filter object to a dict with pinecone filter expressions
            pinecone_filter = self._get_pinecone_filter(query.filter)

            try:
                # Query the index with the query embedding, filter, and top_k
                query_response = self.index.query(
                    # namespace=namespace,
                    top_k=query.top_k,
                    vector=query.embedding,
                    filter=pinecone_filter,
                    include_metadata=True,
                )
            except Exception as e:
                logger.error(f"Error querying index: {e}")
                raise e

            query_results: List[DocumentChunkWithScore] = []
            for result in query_response.matches:
                score = result.score
                metadata = result.metadata
                # Remove document id and text from metadata and store it in a new variable
                metadata_without_text = (
                    {key: value for key, value in metadata.items() if key != "text"}
                    if metadata
                    else None
                )

                # If the source is not a valid Source in the Source enum, set it to None
                if (
                    metadata_without_text
                    and "source" in metadata_without_text
                    and metadata_without_text["source"] not in Source.__members__
                ):
                    metadata_without_text["source"] = None

                # Create a document chunk with score object with the result data
                result = DocumentChunkWithScore(
                    id=result.id,
                    score=score,
                    text=str(metadata["text"])
                    if metadata and "text" in metadata
                    else "",
                    metadata=metadata_without_text,
                )
                query_results.append(result)
            return QueryResult(query=query.query, results=query_results)

        # Use asyncio.gather to run multiple _single_query coroutines concurrently and collect their results
        results: List[QueryResult] = await asyncio.gather(
            *[_single_query(query) for query in queries]
        )

        return results

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything from the index.
        """
        # Delete all vectors from the index if delete_all is True
        if delete_all:
            try:
                logger.info(f"Deleting all vectors from index")
                self.index.delete(delete_all=True)
                logger.info(f"Deleted all vectors successfully")
                return True
            except Exception as e:
                logger.error(f"Error deleting all vectors: {e}")
                raise e

        # Convert the metadata filter object to a dict with pinecone filter expressions
        pinecone_filter = self._get_pinecone_filter(filter)
        # Delete vectors that match the filter from the index if the filter is not empty
        if pinecone_filter != {}:
            try:
                logger.info(f"Deleting vectors with filter {pinecone_filter}")
                self.index.delete(filter=pinecone_filter)
                logger.info(f"Deleted vectors with filter successfully")
            except Exception as e:
                logger.error(f"Error deleting vectors with filter: {e}")
                raise e

        # Delete vectors that match the document ids from the index if the ids list is not empty
        if ids is not None and len(ids) > 0:
            try:
                logger.info(f"Deleting vectors with ids {ids}")
                pinecone_filter = {"document_id": {"$in": ids}}
                self.index.delete(filter=pinecone_filter)  # type: ignore
                logger.info(f"Deleted vectors with ids successfully")
            except Exception as e:
                logger.error(f"Error deleting vectors with ids: {e}")
                raise e

        return True

    def _get_pinecone_filter(
        self, filter: Optional[DocumentMetadataFilter] = None
    ) -> Dict[str, Any]:
        if filter is None:
            return {}

        pinecone_filter = {}

        # For each field in the MetadataFilter, check if it has a value and add the corresponding pinecone filter expression
        # For start_date and end_date, uses the $gte and $lte operators respectively
        # For other fields, uses the $eq operator
        for field, value in filter.dict().items():
            if value is not None:
                if field == "start_date":
                    pinecone_filter["created_at"] = pinecone_filter.get(
                        "created_at", {}
                    )
                    pinecone_filter["created_at"]["$gte"] = to_unix_timestamp(value)
                elif field == "end_date":
                    pinecone_filter["created_at"] = pinecone_filter.get(
                        "created_at", {}
                    )
                    pinecone_filter["created_at"]["$lte"] = to_unix_timestamp(value)
                else:
                    pinecone_filter[field] = value

        return pinecone_filter

    def _get_pinecone_metadata(
        self, metadata: Optional[DocumentChunkMetadata] = None
    ) -> Dict[str, Any]:
        if metadata is None:
            return {}

        pinecone_metadata = {}

        # For each field in the Metadata, check if it has a value and add it to the pinecone metadata dict
        # For fields that are dates, convert them to unix timestamps
        for field, value in metadata.dict().items():
            if value is not None:
                if field in ["created_at"]:
                    pinecone_metadata[field] = to_unix_timestamp(value)
                else:
                    pinecone_metadata[field] = value

        return pinecone_metadata
