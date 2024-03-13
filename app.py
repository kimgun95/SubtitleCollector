import os

import boto3
from dotenv import load_dotenv
from flask import Flask, render_template, request

from src.errors import DynamoOperationError, DynamoDuplicatedError
from src.storage import S3, DynamoDB
from src.youtube import ProcessYoutube

load_dotenv()

app = Flask(__name__)

# SpringBoot AutoWire가 없어서 수동 주입 준비
# DynamoDB와 S3 클라이언트 설정
s3_object = boto3.client('s3', region_name='ap-northeast-2')
dynamodb_object = boto3.resource('dynamodb', region_name='ap-northeast-2')
table_object = dynamodb_object.Table('Subtitle')

# BUCKET_NAME = 'subtitle-collection'
VTT_DIRECTORY = '/subtitle/vtt'
DEBUG = bool(os.getenv('DEBUG'))
if DEBUG is not True:
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


# def get_kst():
#     tz_kst = pytz.timezone('Asia/Seoul')
#     datetime_kst = datetime.now(tz_kst)
#     return datetime_kst.strftime("%Y-%m-%d %H:%M:%S")


# HTML_FORM
# HTML_FORM = """
# """
@app.route('/post/<video_id>')
def post(video_id):
    try:
        # DynamoDB 테이블에서 해당 video_id에 해당하는 게시물 가져오기
        response = table_object.get_item(Key={'video_id': video_id})
        post = response['Item']
        print(post)
    except Exception as e:
        print(f"Error retrieving post from DynamoDB: {e}")
        post = {}

    return render_template('post.html', post=post)

@app.route('/board')
def board():
    try:
        # DynamoDB 테이블에서 모든 게시물 가져오기
        response = table_object.scan()
        posts = response['Items']
    except Exception as e:
        print(f"Error retrieving posts from DynamoDB: {e}")
        posts = []

    return render_template('board.html', posts=posts)

@app.route('/', methods=['GET', 'POST'])
def index():
    error_message = None
    success_message = None

    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url')
        try:
            ProcessYoutube(
                s3=S3(storage_object=s3_object),
                dynamo_table=DynamoDB(storage_object=table_object),
                youtube_url=youtube_url,
                vtt_directory=VTT_DIRECTORY
            )
            success_message = '처리 완료되었습니다.'
        except DynamoOperationError as e:
            error_message = f'중복된 영상입니다: {e}'
        except DynamoDuplicatedError as e:
            error_message = f'중복된 영상입니다: {e}'
        except Exception as e:
            # 기타 등등 잡다한 에러 처리하는 곳.
            error_message = f'에러: {e}'

    return render_template('index.html', error_message=error_message, success_message=success_message)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090, debug=True)
