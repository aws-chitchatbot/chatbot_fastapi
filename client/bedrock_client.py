import os
import boto3
from botocore.config import Config
from models.models import BedrockClient


def get_bedrock_client(config: BedrockClient):
    """선택적 설정 오버라이드을 사용하여 Amazon Bedrock용 boto3 클라이언트 만들기"""
    if config.region is None:
        target_region = os.environ.get(
            "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION")
        )
    else:
        target_region = config.region

    print(f"새로운 클라이언트 생성\n  사용 지역: {target_region}")
    session_kwargs = {"지역 이름": target_region}
    client_kwargs = {**session_kwargs}

    profile_name = os.environ.get("AWS_PROFILE")
    if profile_name:
        print(f"  사용하는 프로파일: {profile_name}")
        session_kwargs["profile_name"] = profile_name

    retry_config = Config(
        region_name=target_region,
        retries={
            "max_attempts": 10,
            "mode": "standard",
        },
    )
    session = boto3.Session(**session_kwargs)

    if config.assumed_role:
        print(f"  사용하는 역할: {config.assumed_role}", end="")
        sts = session.client("sts")
        response = sts.assume_role(
            RoleArn=str(config.assumed_role), RoleSessionName="langchain-llm-1"
        )
        print(" ... successful!")
        client_kwargs["aws_access_key_id"] = response["Credentials"]["AccessKeyId"]
        client_kwargs["aws_secret_access_key"] = response["Credentials"][
            "SecretAccessKey"
        ]
        client_kwargs["aws_session_token"] = response["Credentials"]["SessionToken"]

    if config.runtime:
        service_name = "bedrock-runtime"
    else:
        service_name = "bedrock"

    bedrock_client = session.client(
        service_name=service_name, config=retry_config, **client_kwargs
    )

    print("boto3 Bedrock Client 생성 성공!")
    print(bedrock_client._endpoint)
    return bedrock_client
