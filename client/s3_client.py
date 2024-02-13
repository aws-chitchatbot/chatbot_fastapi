import boto3
from models.models import S3ClientConfig


class S3Client:
    def __init__(self, config: S3ClientConfig):
        self.aws_access_key_id = config.aws_access_key_id
        self.aws_secret_access_key = config.aws_secret_access_key
        self.region_name = config.region_name
        self.bucket_name = config.bucket_name
        self.client = boto3.client(
            "s3",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
        )
        self.bucket_name = self.bucket_name

        # 버킷이 없는 경우 생성
        if not self.check_bucket_exists():
            self.create_bucket()

    def create_bucket(self):
        try:
            self.client.create_bucket(
                Bucket=self.bucket_name,
                CreateBucketConfiguration={"LocationConstraint": self.region_name},
            )
            print(f"버킷 '{self.bucket_name}'이(가) 성공적으로 생성되었습니다.")
        except self.client.exceptions.BucketAlreadyExists as e:
            print(f"버킷 '{self.bucket_name}'은(는) 이미 존재합니다.")
        except self.client.exceptions.BucketAlreadyOwnedByYou as e:
            print(f"버킷 '{self.bucket_name}'은(는) 이미 여러분의 소유입니다.")
        except Exception as e:
            print(f"버킷 '{self.bucket_name}' 생성 중 오류 발생: {e}")

    def check_bucket_exists(self):
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return True
        except Exception as e:
            return False

    def upload_file(self, local_file_path, s3_key):
        """파일을 S3 버킷에 업로드합니다."""
        try:
            self.client.upload_file(local_file_path, self.bucket_name, s3_key)
            print(f"파일 '{s3_key}'이(가) 성공적으로 업로드되었습니다.")
        except Exception as e:
            print(f"파일 업로드 중 오류 발생: {e}")

    def download_file(self, s3_key, local_file_path):
        """S3 버킷에서 파일을 다운로드합니다."""
        try:
            self.client.download_file(self.bucket_name, s3_key, local_file_path)
            print(f"파일 '{s3_key}'이(가) 성공적으로 다운로드되었습니다.")
        except Exception as e:
            print(f"파일 다운로드 중 오류 발생: {e}")

    def delete_bucket(self):
        """S3 버킷과 그 내용을 삭제합니다."""
        if self.check_bucket_exists():
            try:
                objects = self.client.list_objects(Bucket=self.bucket_name).get(
                    "Contents", []
                )
                for obj in objects:
                    self.client.delete_object(Bucket=self.bucket_name, Key=obj["Key"])
                self.client.delete_bucket(Bucket=self.bucket_name)
                print(f"버킷 '{self.bucket_name}'이(가) 성공적으로 삭제되었습니다.")
            except Exception as e:
                print(f"버킷 삭제 중 오류 발생: {e}")
        else:
            print(f"버킷 '{self.bucket_name}'이(가) 존재하지 않습니다.")

    def delete_file(self, s3_key):
        """S3 버킷에서 파일을 삭제합니다."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            print(f"파일 '{s3_key}'이(가) 성공적으로 삭제되었습니다.")
        except Exception as e:
            print(f"파일 삭제 중 오류 발생: {e}")
