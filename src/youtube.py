import json
import os
import subprocess
import re


class Youtube:
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
            return None

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
            print(f"yt-dlp error: {result.stderr}")
            return None, result.stderr

        expected_filename = vtt_filename.replace("%(ext)s", "en")
        if os.path.exists(expected_filename):
            return expected_filename, None
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
        except FileNotFoundError:
            print("File not found.")
        return ' '.join(content)
