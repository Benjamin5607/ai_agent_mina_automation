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
        # 텍스트만 추출하고 쓸데없는 공백 제거 (너무 길면 잘라냄)
        text = ' '.join(soup.stripped_strings)
        return f"📄 [웹페이지 크롤링 완료]\n{text[:3000]}..." 
    except Exception as e:
        return f"웹페이지 접근 실패: {e}"

def use_file_system(action, filepath, content=""):
    """💾 로컬 파일 읽기/쓰기 (저장소 무제한 무료)"""
    try:
        if action == "write":
            # 파일을 덮어쓰거나 새로 만듭니다.
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
    """💻 로컬 파이썬 터미널 실행기 (오토GPT의 핵심!)"""
    try:
        # 에이전트가 짠 코드를 임시 파일로 만들고 실행해버립니다.
        with open("temp_agent_script.py", "w", encoding="utf-8") as f:
            f.write(code)
        
        # 무한 루프 방지를 위해 10초 타임아웃 설정
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

# ---------------------------------------------------------
# 🔑 [기존 유료/Key 필요] 무기들
# ---------------------------------------------------------
def use_notion_api(title, content, api_key, database_id):
    """📝 Notion API"""
    if not api_key or not database_id: return "🚨 에러: NOTION 키가 없습니다."
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    
    # 📌 여기서 괄호 에러가 났었습니다! 깔끔하게 수정 완료!
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
        if action == "write":
            # 파일을 덮어쓰거나 새로 만듭니다.
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
    """💻 로컬 파이썬 터미널 실행기 (오토GPT의 핵심!)"""
    try:
        # 에이전트가 짠 코드를 임시 파일로 만들고 실행해버립니다.
        with open("temp_agent_script.py", "w", encoding="utf-8") as f:
            f.write(code)
        
        # 무한 루프 방지를 위해 10초 타임아웃 설정
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

# ---------------------------------------------------------
# 🔑 [기존 유료/Key 필요] 무기들
# ---------------------------------------------------------
def use_notion_api(title, content, api_key, database_id):
    """📝 Notion API"""
    if not api_key or not database_id: return "🚨 에러: NOTION 키가 없습니다."
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    blocks = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": chunk.strip()[:1900]}}]}}] for chunk in content.split("\n\n") if chunk.strip()]
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
