from datetime import datetime

import pytz


def get_kst():
    tz_kst = pytz.timezone('Asia/Seoul')
    datetime_kst = datetime.now(tz_kst)
    return datetime_kst.strftime("%Y-%m-%d %H:%M:%S")
