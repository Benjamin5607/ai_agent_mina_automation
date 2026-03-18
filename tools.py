import requests
import json
import os
import subprocess
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# ---------------------------------------------------------
# 🆓 [100% 무료 / No API Key / No Credit Card] 무기 라인업
# ---------------------------------------------------------

def use_duckduckgo_search(query):
    """🦆 무제한 무료 검색 (DuckDuckGo)"""
    try:
        results = DDGS().text(query, max_results=3)
        if not results: return "검색 결과가 없습니다."
        formatted = [f"제목: {r['title']}\n링크: {r['href']}\n요약: {r['body']}" for r in results]
        return "🔍 [무료 웹 검색 완료]\n" + "\n\n".join(formatted)
    except Exception as e:
        return f"검색 중 에러: {e}"

def use_web_scraper(url):
    """🕷️ 무제한 웹페이지 본문 스크래퍼"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        text = ' '.join(soup.stripped_strings)
        return f"📄 [웹페이지 크롤링 완료]\n{text[:3000]}..." 
    except Exception as e:
        return f"웹페이지 접근 실패: {e}"

def use_file_system(action, filepath, content=""):
    """💾 로컬 파일 읽기/쓰기"""
    try:
        if action == "write":
            if os.path.dirname(filepath):
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"💾 [파일 저장 완료] {filepath} 에 내용이 저장되었습니다."
        elif action == "read":
            if not os.path.exists(filepath): return f"에러: {filepath} 파일이 없습니다."
            with open(filepath, 'r', encoding='utf-8') as f:
                return f"📖 [파일 읽기 완료] {filepath} 내용:\n{f.read()[:2000]}..."
    except Exception as e:
        return f"파일 시스템 에러: {e}"

def use_python_executor(code):
    """💻 로컬 파이썬 터미널 실행기"""
    try:
        with open("temp_agent_script.py", "w", encoding="utf-8") as f:
            f.write(code)
        
        result = subprocess.run(["python", "temp_agent_script.py"], capture_output=True, text=True, timeout=10)
        
        output = result.stdout if result.stdout else ""
        error = result.stderr if result.stderr else ""
        
        if result.returncode == 0:
            return f"✅ [파이썬 실행 성공]\n출력 결과:\n{output}"
        else:
            return f"❌ [파이썬 실행 에러]\n{error}"
    except subprocess.TimeoutExpired:
        return "⏳ 파이썬 실행 타임아웃 (10초 초과로 강제 종료됨)"
    except Exception as e:
        return f"실행기 에러: {e}"

def use_video_generator(script, visual_prompt):
    """🎬 숏폼 영상 제작기 (무료: Moviepy + gTTS + Pollinations)"""
    try:
        import urllib.parse
        from gtts import gTTS
        import moviepy.editor as mp
        
        # 1. Emily 캐릭터 이미지 생성 (무료 AI API)
        safe_prompt = urllib.parse.quote(visual_prompt)
        img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}"
        img_data = requests.get(img_url).content
        with open("emily_bg.jpg", "wb") as f:
            f.write(img_data)
            
        # 2. AI 성우 대본 녹음 (무료 gTTS)
        tts = gTTS(text=script, lang='ko') # 영어로 하려면 'en'
        tts.save("emily_voice.mp3")
        
        # 3. 오디오 길이에 맞춰 영상 렌더링
        audio = mp.AudioFileClip("emily_voice.mp3")
        img_clip = mp.ImageClip("emily_bg.jpg").set_duration(audio.duration)
        video = img_clip.set_audio(audio)
        
        # mp4 파일로 굽기
        output_filename = "emily_shorts.mp4"
        video.write_videofile(output_filename, fps=24, logger=None)
        
        return f"🎬 [영상 제작 완료] '{output_filename}' (길이: {round(audio.duration, 1)}초) 파일이 성공적으로 렌더링되었습니다!"
    except Exception as e:
        return f"영상 제작 에러: {e}"

def use_sns_webhook(video_title, tags, webhook_url):
    """🚀 SNS 자동 업로드 (Make/Zapier 웹훅 연동)"""
    if not webhook_url: return "🚨 에러: WEBHOOK_URL이 입력되지 않았습니다."
    try:
        # 워커가 만든 영상 정보를 Make.com으로 전송
        payload = {
            "title": video_title,
            "tags": tags,
            "video_file": "emily_shorts.mp4",
            "action": "post_to_tiktok_instagram_youtube"
        }
        res = requests.post(webhook_url, json=payload)
        return f"✅ [SNS 업로드 신호 전송 완료] Make.com 웹훅이 정상적으로 영상을 넘겨받아 배포를 시작합니다! (상태코드: {res.status_code})"
    except Exception as e:
        return f"웹훅 전송 에러: {e}"

# ---------------------------------------------------------
# 🔑 [기존 유료/Key 필요] 무기들
# ---------------------------------------------------------
def use_notion_api(title, content, api_key, database_id):
    """📝 Notion API"""
    if not api_key or not database_id: return "🚨 에러: NOTION 키가 없습니다."
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    
    blocks = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": chunk.strip()[:1900]}}]}} for chunk in content.split("\n\n") if chunk.strip()]
    
    payload = {"parent": {"database_id": database_id}, "properties": {"title": {"title": [{"text": {"content": title}}]}}, "children": blocks[:100]}
    try:
        res = requests.post(url, headers=headers, json=payload)
        return f"✅ [노션 작성 완료] 링크: {res.json().get('url')}" if res.status_code == 200 else f"노션 실패: {res.text}"
    except Exception as e: return f"노션 에러: {e}"

def use_slack_api(message, api_key, channel="#general"):
    """💬 Slack API"""
    if not api_key: return "🚨 에러: SLACK_BOT_TOKEN이 없습니다."
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        res = requests.post(url, headers=headers, json={"channel": channel, "text": message})
        return f"✅ [슬랙 전송 완료]" if res.status_code == 200 else f"슬랙 실패"
    except Exception as e: return f"슬랙 에러: {e}"
