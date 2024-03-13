import re
from datetime import datetime

import pytz


def get_kst():
    tz_kst = pytz.timezone('Asia/Seoul')
    datetime_kst = datetime.now(tz_kst)
    return datetime_kst.strftime("%Y-%m-%d %H:%M:%S")


def extract_video_id(youtube_url):
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)',
        r'(?:https?:\/\/)?youtu\.be\/([^?\n]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    raise ValueError(f"형식에 맞지 않습니다.")
