import requests
import json
import streamlit as st

def use_web_crawler(query, api_key):
    """🌐 Web Crawler (Tavily API)"""
    if not api_key: return "🚨 에러: TAVILY_API_KEY가 없습니다."
    url = "https://api.tavily.com/search"
    payload = {"api_key": api_key, "query": query, "search_depth": "basic", "max_results": 3}
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            data = res.json()
            results = [f"제목: {r['title']}\n내용: {r['content']}\n출처: {r['url']}" for r in data.get('results', [])]
            return "🔍 [웹 검색 완료]\n" + "\n\n".join(results) if results else "검색 결과가 없습니다."
        return f"웹 검색 실패: {res.text}"
    except Exception as e:
        return f"웹 검색 중 시스템 에러: {e}"

def use_notion_api(title, content, api_key, database_id):
    """📝 Notion API (SSOT 문단 블록 파싱 적용)"""
    if not api_key or not database_id: return "🚨 에러: NOTION_API_KEY 또는 NOTION_DATABASE_ID가 없습니다."
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    
    # 📌 핵심: 긴 글을 문단 단위로 잘라서 노션의 개별 '블록'으로 만듭니다. (가독성 폭발)
    blocks = []
    for chunk in content.split("\n\n"):
        if chunk.strip():
            blocks.append({
                "object": "block", 
                "type": "paragraph", 
                "paragraph": {"rich_text": [{"text": {"content": chunk.strip()[:1900]}}]}
            })
            
    payload = {
        "parent": {"database_id": database_id},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": blocks[:100] # 노션 API는 한 번에 100개 블록까지만 허용
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            return f"✅ [노션 SSOT 작성 완료] 깔끔하게 구조화된 문서가 업로드되었습니다! 링크: {res.json().get('url')}"
        return f"노션 작성 실패: {res.text}"
    except Exception as e:
        return f"노션 API 에러: {e}"

def use_slack_api(message, api_key, channel="#general"):
    """💬 Slack API"""
    if not api_key: return "🚨 에러: SLACK_BOT_TOKEN이 없습니다."
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"channel": channel, "text": message}
    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200 and res.json().get("ok"):
            return f"✅ [슬랙 전송 완료] '{channel}' 채널에 메시지를 보냈습니다."
        return f"슬랙 전송 실패: {res.json().get('error')}"
    except Exception as e:
        return f"슬랙 API 에러: {e}"

def use_pixabay_api(query, api_key):
    """🎨 Pixabay API"""
    if not api_key: return "🚨 에러: PIXABAY_API_KEY가 없습니다."
    url = f"https://pixabay.com/api/?key={api_key}&q={query}&image_type=photo&per_page=3"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            images = [hit['largeImageURL'] for hit in data.get('hits', [])]
            return "🎨 [이미지 검색 완료]\n" + "\n".join(images) if images else "관련 이미지를 찾지 못했습니다."
        return f"이미지 검색 실패: {res.text}"
    except Exception as e:
        return f"픽사베이 API 에러: {e}"
