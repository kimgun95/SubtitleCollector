import os

import boto3
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for
from boto3.dynamodb.conditions import Key

from src.errors import DynamoOperationError, DynamoDuplicatedError
from src.storage import DynamoDB
from src.youtube import ProcessYoutube

load_dotenv()

app = Flask(__name__)

# SpringBoot AutoWire가 없어서 수동 주입 준비
# DynamoDB와 S3 클라이언트 설정
s3_object = boto3.client('s3', region_name='ap-northeast-2')
dynamodb_object = boto3.resource('dynamodb', region_name='ap-northeast-2')
table_object = dynamodb_object.Table('Subtitle-Ondemand')

# BUCKET_NAME = 'subtitle-collection'
VTT_DIRECTORY = '/subtitle/vtt'
DEBUG = bool(os.getenv('DEBUG'))
if DEBUG is not True:
    os.makedirs(VTT_DIRECTORY, exist_ok=True)

def pagination(data, page, per_page):
    total_pages = len(data) // per_page + 1
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_data = data[start_idx:end_idx]
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None
    return paginated_data, prev_page, next_page, total_pages


@app.route('/search')
def search():
    search_query = request.args.get('q')
    search_field = request.args.get('search_field')

    if not search_query or not search_field:
        # 검색어 또는 검색 필드가 제공되지 않은 경우
        return "검색어와 검색 필드를 모두 제공해야 합니다."

    if search_field == 'leetcode_number':
        try:
            print('검색한 숫자 값: ', int(search_query))
            print('검색한 숫자 값 타입: ', type(int(search_query)))
            response = table_object.query(
                # TableName='your_table_name',
                IndexName='leetcode_number_index',  # 생성한 글로벌 보조 인덱스 이름
                KeyConditionExpression='leetcode_number = :number',
                ExpressionAttributeValues={
                    ':number': {'N': str(search_query)}  # leetcode_number는 숫자형이므로 문자열로 변환하여 전달
                }
            )
            search_results = response['Items']
            print("검색된 포스트의 총 갯수:", len(search_results))
        except Exception as e:
            print(f"Error searching by leetcode_number: {e}")
            search_results = []
    else:
        # 올바르지 않은 검색 필드를 선택한 경우
        return "올바른 검색 필드를 선택하세요 (title 또는 leetcode_number)."

    page = int(request.args.get('page', 1))  # 페이지 번호, 기본값은 1
    per_page = 10  # 페이지당 게시물 수

    posts, prev_page, next_page, total_pages = pagination(search_results, page, per_page)

    for post in posts:
        print("포스트의 제목: " + post.title)

    return render_template('board.html', posts=posts, prev_page=prev_page, next_page=next_page, total_pages=total_pages)

@app.route('/update_post/<video_id>', methods=['POST'])
def update_post(video_id):
    try:
        # 새로운 content
        new_content = request.form.get('content')

        # 실제로 업데이트 작업을 수행하는 코드
        response = table_object.update_item(
            Key={
                'video_id': video_id
            },
            UpdateExpression='SET content = :val',
            ExpressionAttributeValues={
                ':val': new_content
            }
        )
        print("Post updated successfully")

        # 업데이트가 성공하면 post 페이지로 리다이렉트합니다.
        return redirect(url_for('post', video_id=video_id))
    except Exception as e:
        print(f"Error updating post: {e}")
        # 실패할 경우 에러 메시지를 출력하고 이전 페이지로 리다이렉트합니다.
        return redirect(request.referrer or url_for('board'))  # 이전 페이지로 리다이렉트

@app.route('/delete_post/<video_id>', methods=['POST'])
def delete_post(video_id):
    try:
        # 여기에 삭제 작업을 수행하는 코드를 추가하세요
        table_object.delete_item(
            Key={
                'video_id': video_id
            }
        )
        print("Post deleted successfully")
        # 삭제가 성공하면 게시판 페이지로 리다이렉트합니다.
        return redirect(url_for('board'))
    except Exception as e:
        print(f"Error deleting post: {e}")
        # 실패할 경우 에러 메시지를 출력하고 이전 페이지로 리다이렉트합니다.
        return redirect(request.referrer or url_for('board'))  # 이전 페이지로 리다이렉트

@app.route('/post/<video_id>')
def post(video_id):
    try:
        response = table_object.get_item(Key={'video_id': video_id})
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
        all_posts = response['Items']
    except Exception as e:
        print(f"Error retrieving posts from DynamoDB: {e}")
        all_posts = []

    page = int(request.args.get('page', 1))  # 페이지 번호, 기본값은 1
    per_page = 10  # 페이지당 게시물 수

    posts, prev_page, next_page, total_pages = pagination(all_posts, page, per_page)

    return render_template('board.html', posts=posts, prev_page=prev_page, next_page=next_page, total_pages=total_pages)

@app.route('/', methods=['GET', 'POST'])
def index():
    error_message = None
    success_message = None

    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url')
        leetcode_number = request.form.get('leetcode_number')
        try:
            ProcessYoutube(
                # s3=S3(storage_object=s3_object),
                dynamo_table=DynamoDB(storage_object=table_object),
                youtube_url=youtube_url,
                vtt_directory=VTT_DIRECTORY,
                leetcode_number=int(leetcode_number)
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
