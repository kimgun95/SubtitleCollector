import os

import boto3
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for

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


@app.route('/update_post/<video_id>/<title>', methods=['POST'])
def update_post(video_id, title):
    try:
        # 새로운 content
        new_content = request.form.get('content')

        # 실제로 업데이트 작업을 수행하는 코드
        response = table_object.update_item(
            Key={
                'video_id': video_id,
                'title': title
            },
            UpdateExpression='SET content = :val',
            ExpressionAttributeValues={
                ':val': new_content
            }
        )
        print("Post updated successfully")

        # 업데이트가 성공하면 post 페이지로 리다이렉트합니다.
        return redirect(url_for('post', video_id=video_id, title=title))
    except Exception as e:
        print(f"Error updating post: {e}")
        # 실패할 경우 에러 메시지를 출력하고 이전 페이지로 리다이렉트합니다.
        return redirect(request.referrer or url_for('board'))  # 이전 페이지로 리다이렉트

@app.route('/delete_post/<video_id>/<title>', methods=['POST'])
def delete_post(video_id, title):
    try:
        # 여기에 삭제 작업을 수행하는 코드를 추가하세요
        table_object.delete_item(
            Key={
                'video_id': video_id,
                'title': title
            }
        )
        print("Post deleted successfully")
        # 삭제가 성공하면 게시판 페이지로 리다이렉트합니다.
        return redirect(url_for('board'))
    except Exception as e:
        print(f"Error deleting post: {e}")
        # 실패할 경우 에러 메시지를 출력하고 이전 페이지로 리다이렉트합니다.
        return redirect(request.referrer or url_for('board'))  # 이전 페이지로 리다이렉트

@app.route('/post/<video_id>/<title>')
def post(video_id, title):
    try:
        response = table_object.get_item(Key={'video_id': video_id, 'title': title})
        post = response.get('Item', {})

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
