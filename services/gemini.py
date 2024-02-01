from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
from tenacity import retry, wait_random_exponential, stop_after_attempt


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    google bard models/embedding-001 모델을 사용하여 텍스트를 임베딩합니다.

    Args:
        텍스트: 임베드할 텍스트 목록입니다.

    return:
        임베딩 목록, 각 임베딩은 플로트 리스트입니다.

    Raises:
        예외: gemini-pro API 호출이 실패한 경우.
    """
    # gemini-pro API를 호출하여 임베딩 가져오기
    deployment = os.environ.get("GOOGLE_EMBEDDINGMODEL_DEPLOYMENTID")
    response = {}
    if deployment == None:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        response = embeddings.embed_documents(texts=texts)
    else:
        embeddings = GoogleGenerativeAIEmbeddings(model=deployment)
        response = embeddings.embed_documents(texts=texts)

    # # 응답에서 임베딩 데이터 추출하기
    # data = response["data"]

    # # 임베딩을 플로트 리스트 목록으로 반환합니다.
    # return [result["embedding"] for result in data]
    return response
