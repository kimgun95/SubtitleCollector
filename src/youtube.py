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
                    return os.path.join(vtt_directory, file), None
            return None, "Subtitle file not found after yt-dlp execution."

    @staticmethod
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
