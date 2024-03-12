import os
from datetime import datetime

import boto3
import pytz
from flask import Flask

app = Flask(__name__)

# DynamoDB와 S3 클라이언트 설정
dynamodb_object = boto3.resource('dynamodb', region_name='ap-northeast-2')
s3_object = boto3.client('s3', region_name='ap-northeast-2')
table = dynamodb_object.Table('Subtitle')
BUCKET_NAME = 'subtitle-collection'

VTT_DIRECTORY = '/subtitle/vtt'
os.makedirs(VTT_DIRECTORY, exist_ok=True)


# next_num = 100000


# def extract_video_id(youtube_url):
#     patterns = [
#         r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)',
#         r'(?:https?:\/\/)?youtu\.be\/([^?\n]+)',
#     ]
#     for pattern in patterns:
#         match = re.search(pattern, youtube_url)
#         if match:
#             return match.group(1)
#     return None


# def check_video_exists_in_dynamodb(video_id, title):
#     try:
#         # video_id와 title을 사용하여 DynamoDB에서 항목을 조회합니다.
#         response = table.get_item(Key={'video_id': video_id, 'title': title})
#         return 'Item' in response
#     except Exception as e:
#         print(f"Error checking video in DynamoDB: {e}")
#         return False


# def get_next_num():
#     global next_num
#     next_num += 1
#     return next_num


# def process_vtt_content(vtt_filename):
#     content = []
#     try:
#         with open(vtt_filename, 'r', encoding='utf-8') as file:
#             for line in file:
#                 if '-->' in line:
#                     continue
#                 line = re.sub(r'<[^>]+>', '', line)
#                 content.append(line.strip())
#         os.remove(vtt_filename)
#     except FileNotFoundError:
#         print("File not found.")
#     return ' '.join(content)


# def save_to_s3(video_id, title, datetime, content):
#     clean_content = content.replace('\n', ' ')
#     csv_content = f"\"{video_id}\",\"{title}\",\"{datetime}\",\"{content}\"\n"
#     filename = f"{datetime[:10]}.csv"
#     try:
#         existing_object = s3_object.get_object(Bucket=BUCKET_NAME, Key=filename)
#         existing_content = existing_object['Body'].read().decode('utf-8')
#         csv_content = existing_content + csv_content
#     except s3_object.exceptions.NoSuchKey:
#         csv_content = "video_id,title,datetime,content\n" + csv_content
#     s3_object.put_object(Bucket=BUCKET_NAME, Key=filename, Body=csv_content, ContentType='text/csv')


# def save_to_dynamodb(video_id, title, datetime, content):
#     try:
#         table.put_item(
#             Item={
#                 'video_id': video_id,
#                 'title': title,
#                 'datetime': datetime,
#                 'content': content
#             }
#         )
#     except Exception as e:
#         print(f"Error saving to DynamoDB: {e}")


def get_kst():
    tz_kst = pytz.timezone('Asia/Seoul')
    datetime_kst = datetime.now(tz_kst)
    return datetime_kst.strftime("%Y-%m-%d %H:%M:%S")


# HTML_FORM
# HTML_FORM = """
# """


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url')
        if youtube_url:
            video_id = extract_video_id(youtube_url)
            if not video_id:
                return '유효하지 않은 YouTube URL입니다. 올바른 URL을 입력해주세요.'

            video_info = get_video_info(youtube_url)
            if not video_info:
                return '영상 정보를 추출하는데 실패했습니다. URL을 확인해주세요.'

            title = video_info.get('title', '제목 없음')
            datetime_str = get_kst()

            if check_video_exists_in_dynamodb(video_id, title):
                return '이미 입력되어 있는 영상입니다.'

            vtt_path, error = extract_subtitles(youtube_url, video_id)
            if error:
                return f"자막 추출 중 오류가 발생했습니다: {error}"

            content = process_vtt_content(vtt_path)
            if content:
                save_to_dynamodb(video_id, title, datetime_str, content)
                save_to_s3(video_id, title, datetime_str, content)  # 올바른 인자를 사용하여 함수를 호출합니다.
                return '처리 완료되었습니다.'
            else:
                return '자막을 추출하지 못했습니다. 영상에 자막이 없거나 다른 문제가 발생했을 수 있습니다.'
        return '유효하지 않은 URL입니다. 정확한 YouTube URL을 입력해주세요.'
    else:
        return render_template_string(HTML_FORM)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090, debug=True)
