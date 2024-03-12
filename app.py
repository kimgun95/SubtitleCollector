from flask import Flask, request, render_template_string
import boto3
from datetime import datetime
import os
import subprocess
import re
import pytz
import json

app = Flask(__name__)

dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
s3 = boto3.client('s3', region_name='ap-northeast-2')
table = dynamodb.Table('Subtitle')
bucket_name = 'subtitle-collection'

vtt_directory = '/subtitle/vtt'
os.makedirs(vtt_directory, exist_ok=True)

next_num = 100000

def extract_video_id(youtube_url):
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)',
        r'(?:https?:\/\/)?youtu\.be\/([^?\n]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    return None

def check_video_exists_in_dynamodb(video_id):
    try:
        response = table.get_item(Key={'video_id': video_id})
        return 'Item' in response
    except Exception as e:
        print(f"Error checking video in DynamoDB: {e}")
        return False

def get_next_num():
    global next_num
    next_num += 1
    return next_num

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
        return None

def extract_subtitles(url, num):
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
        print(f"yt-dlp error: {result.stderr}")
        return None, result.stderr

    expected_filename = vtt_filename.replace("%(ext)s", "en")
    if os.path.exists(expected_filename):
        return expected_filename, None
    else:
        for file in os.listdir(vtt_directory):
            if file.startswith(str(num)) and file.endswith(".vtt"):
                return os.path.join(vtt_directory, file), None
        return None, "Subtitle file not found after yt-dlp execution."

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
    except FileNotFoundError:
        print("File not found.")
    return ' '.join(content)

def save_to_dynamodb(video_id, subtitle, datetime, link, content):
    table.put_item(
        Item={
            'video_id': video_id,
            'subtitle': subtitle,
            'datetime': datetime,
            'link': link,
            'content': content
        }
    )

def save_to_s3(num, subtitle, datetime, link, content):
    clean_content = content.replace('\n', ' ')
    csv_content = f"\"{num}\",\"{subtitle}\",\"{datetime}\",\"{link}\",\"{clean_content}\"\n"
    filename = f"{datetime[:10]}.csv"
    try:
        existing_object = s3.get_object(Bucket=bucket_name, Key=filename)
        existing_content = existing_object['Body'].read().decode('utf-8')
        csv_content = existing_content + csv_content
    except s3.exceptions.NoSuchKey:
        csv_content = "Num,Subtitle,Datetime,Link,Content\n" + csv_content
    s3.put_object(Bucket=bucket_name, Key=filename, Body=csv_content, ContentType='text/csv')

def get_kst():
    tz_kst = pytz.timezone('Asia/Seoul')
    datetime_kst = datetime.now(tz_kst)
    return datetime_kst.strftime("%Y-%m-%d %H:%M:%S")

# 웹 페이지의 HTML 폼이 여기에 다시 포함됩니다

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url')
        if youtube_url:
            video_id = extract_video_id(youtube_url)
            if not video_id:
                return '유효하지 않은 YouTube URL입니다. 올바른 URL을 입력해주세요.'
            
            if check_video_exists_in_dynamodb(video_id):
                return '이미 입력되어 있는 영상입니다.'
            
            num = get_next_num()
            video_info = get_video_info(youtube_url)
            if not video_info:
                return '영상 정보를 추출하는데 실패했습니다. URL을 확인해주세요.'

            subtitle = video_info.get('title', '제목 없음')
            vtt_filename, error_message = extract_subtitles(youtube_url, num)
            if error_message:
                return f'자막 추출 실패: {error_message}'

            if vtt_filename:
                content = process_vtt_content(vtt_filename)
                datetime_str = get_kst()
                save_to_dynamodb(video_id, subtitle, datetime_str, youtube_url, content)
                save_to_s3(num, subtitle, datetime_str, youtube_url, content)
                return '처리 완료되었습니다.'
            else:
                return '자막을 추출하지 못했습니다. 영상에 자막이 없거나 다른 문제가 발생했을 수 있습니다.'
        return '유효하지 않은 URL입니다. 정확한 YouTube URL을 입력해주세요.'
    return render_template_string(HTML_FORM)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090, debug=True)

