from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class Source(str, Enum):
    email = "email"
    file = "file"
    chat = "chat"


class DocumentMetadata(BaseModel):
    source: Optional[Source] = None
    source_id: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    author: Optional[str] = None


class DocumentChunkMetadata(DocumentMetadata):
    document_id: Optional[str] = None


class DocumentChunk(BaseModel):
    id: Optional[str] = None
    text: str
    metadata: DocumentChunkMetadata
    embedding: Optional[List[float]] = None


class DocumentChunkWithScore(DocumentChunk):
    score: float


class Document(BaseModel):
    id: Optional[str] = None
    text: str
    metadata: Optional[DocumentMetadata] = None


class DocumentWithChunks(Document):
    chunks: List[DocumentChunk]


class DocumentMetadataFilter(BaseModel):
    document_id: Optional[str] = None
    source: Optional[Source] = None
    source_id: Optional[str] = None
    author: Optional[str] = None
    start_date: Optional[str] = None  # any date string format
    end_date: Optional[str] = None  # any date string format


class Query(BaseModel):
    query: str
    filter: Optional[DocumentMetadataFilter] = None
    top_k: Optional[int] = 3


class QueryWithEmbedding(Query):
    embedding: List[float]


class QueryResult(BaseModel):
    query: str
    results: List[DocumentChunkWithScore]


class S3ClientConfig(BaseModel):
    aws_access_key_id: str
    aws_secret_access_key: str
    region_name: str
    bucket_name: str


class BedrockClient(BaseModel):
    """

    매개 변수
    ----------
    assumed_role : Optional[str]
                   default -> None
    Bedrock 서비스를 호출할 때 가정할 AWS IAM 역할의 선택적 ARN입니다. 지정하지 않으면 현재 활성 자격 증명이 사용된다.

    region : Optional[str]
                   default -> None
    서비스를 호출해야 하는 AWS 리전의 이름(예: "us-east-1").
    지정하지 않으면 AWS_REGION 또는 AWS_DEFAULT_REGION 환경 변수가 사용된다.

    runtime : Optional[bool]
                   default -> True
        Amazon Bedrock 서비스에서 작업을 수행할 다른 클라이언트를 가져오는 선택 사항이다.
    """

    assumed_role: Optional[str] = (None,)
    region: Optional[str] = (None,)
    runtime: Optional[bool] = (True,)
