# 기본 이미지 설정
FROM python:3.12.0-slim

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# yt-dlp 설치
RUN apt-get update && \
    apt-get install -y curl && \
    curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# 애플리케이션 파일 복사
COPY . .

# 포트 설정
EXPOSE 9090

# 애플리케이션 실행 명령어
CMD ["python", "app.py"]

