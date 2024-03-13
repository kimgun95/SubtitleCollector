import json
import os
import re
import subprocess

from src.storage import DynamoDB, S3, Storage
from src.utils import get_kst, extract_video_id


class Youtube:
    """
    yt-dlp와 관련된 로직만 따로 모아둔 클래스 입니다.
    외부적으로 이 클래스를 사용할 일이 없습니다.
    """

    @staticmethod
    def get_video_info(url):
        command = [
            'yt-dlp',
            '-J',
            url
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            s = f'''
            영상 정보를 추출하는데 실패했습니다. 
            URL을 확인해주세요: {url=}
            return code: {result.returncode}
            '''
            raise Exception(s)

    @staticmethod
    def extract_subtitles(url, num, vtt_directory):
        vtt_filename = os.path.join(vtt_directory, f"{num}.%(ext)s.vtt")
        command = [
            'yt-dlp',
            '--write-auto-sub',
            '--sub-lang', 'en',
            '--skip-download',
            '--sub-format', 'vtt',
            '-o', vtt_filename,
            url
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            # print(f"yt-dlp error: {result.stderr}") # logger로 따로 처리하세요.
            raise Exception(f"yt-dlp error: {result.stderr}")

        expected_filename = vtt_filename.replace("%(ext)s", "en")
        if os.path.exists(expected_filename):
            return expected_filename
        else:
            for file in os.listdir(vtt_directory):
                if file.startswith(str(num)) and file.endswith(".vtt"):
                    return os.path.join(vtt_directory, file)
            raise Exception(f"yt-dlp 실행 이후 자막 파일을 찾지 못하였습니다.")

    @staticmethod
    def process_vtt_content(vtt_filename):
        content = []
        try:
            with open(vtt_filename, 'r', encoding='utf-8') as file:
                for line in file:
                    if '-->' in line:
                        continue
                    line = re.sub(r'<[^>]+>', '', line)
                    content.append(line.strip())
            os.remove(vtt_filename)
        except FileNotFoundError as e:
            # print("File not found.") # logger로 따로 처리하세요.
            raise Exception(f"파일을 찾지 못하였습니다: {e}")

        if result := ' '.join(content):
            return result
        else:
            raise Exception('자막을 추출하지 못했습니다. 영상에 자막이 없거나 다른 문제가 발생했을 수 있습니다.')


class ProcessYoutube:
    """
    이 클래스를 실행하는 것 자체로 자막 처리를 마칩니다.
    """

    def __init__(self, dynamo_table: DynamoDB | Storage, s3: S3 | Storage, youtube_url: str, vtt_directory: str):
        # DI
        self.dynamo_table = dynamo_table
        self.s3 = s3

        # logic
        video_id = extract_video_id(youtube_url)  # throw 되는 exception들은 여기서 처리 하지 않습니다.
        video_info = Youtube.get_video_info(video_id)  # throw 되는 exception들은 여기서 처리 하지 않습니다.

        title = video_info.get('title', '제목 없음')
        datetime_str = get_kst()

        self.dynamo_table.check_video_exists_in_dynamodb(video_id, title)

        # throw 되는 exception들은 여기서 처리 하지 않습니다.
        vtt_path = Youtube.extract_subtitles(youtube_url, video_id, vtt_directory)

        content = Youtube.process_vtt_content(vtt_path)  # throw 되는 exception들은 여기서 처리 하지 않습니다.
        self.dynamo_table.save_to(video_id, title, datetime_str, content)  # throw 되는 exception들은 여기서 처리 하지 않습니다.
        self.s3.save_to(video_id, title, datetime_str, content)  # throw 되는 exception들은 여기서 처리 하지 않습니다.
