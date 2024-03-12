from abc import ABC, abstractmethod

from src.errors import DynamoDuplicatedError, DynamoOperationError

BUCKET_NAME = 'subtitle-collection'


class Storage(ABC):
    def __init__(self, storage_object):
        """
        공통적인 로직을 실행하는 인터페이스 (추상클래스) 입니다.
        :param storage_object: S3의 경우 S3 object를, 다이나모라면 table까지 설정해서 DI 해주면 됩니다.
        """
        self.storage = storage_object

    @abstractmethod
    def save_to(self, video_id, title, datetime, content):
        ...


class S3(Storage):
    def save_to(self, video_id, title, datetime, content):
        content = content.replace('\n', ' ')
        csv_content = f"\"{video_id}\",\"{title}\",\"{datetime}\",\"{content}\"\n"
        filename = f"{datetime[:10]}.csv"
        try:
            existing_object = self.storage.get_object(Bucket=BUCKET_NAME, Key=filename)
            existing_content = existing_object['Body'].read().decode('utf-8')
            csv_content = existing_content + csv_content
        except self.storage.exceptions.NoSuchKey:
            csv_content = "video_id,title,datetime,content\n" + csv_content
        self.storage.put_object(Bucket=BUCKET_NAME, Key=filename, Body=csv_content, ContentType='text/csv')


class DynamoDB(Storage):
    def save_to(self, video_id, title, datetime, content):
        try:
            self.storage.put_item(
                Item={
                    'video_id': video_id,
                    'title': title,
                    'datetime': datetime,
                    'content': content
                }
            )
        except Exception as e:
            # print(f"Error saving to DynamoDB: {e}") # logger로 따로 처리하세요
            raise DynamoOperationError(f'DynamoDB 저장 에러: {e}')

    def check_video_exists_in_dynamodb(self, video_id, title):
        try:
            # video_id와 title을 사용하여 DynamoDB에서 항목을 조회합니다.
            response = self.storage.get_item(Key={'video_id': video_id, 'title': title})
            return 'Item' in response
        except Exception as e:
            # print(f"Error checking video in DynamoDB: {e}") # logger로 따로 처리하세요
            # return False # False를 리턴 한 이유는 중복 처리를 확인 하는거니깐 따로 처리 해 줍니다.

            if 'AccessDeniedException' in str(e):
                # 접근 권한이 없을 때 raise 하는 분기입니다.
                raise Exception(str(e))
            else:
                # 중복 처리된 영상이 있을 때 raise 하는 분기입니다.
                raise DynamoDuplicatedError(f'{e}')
