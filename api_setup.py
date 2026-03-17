import requests
import streamlit as st

def get_secrets():
    try:
        return {
            "GROQ": st.secrets["GROQ_API_KEY"],
            "GEMINI": st.secrets["GEMINI_API_KEY"],
            "DISCORD": st.secrets["DISCORD_WEBHOOK_URL"]
        }
    except KeyError:
        st.error("🚨 Streamlit Secrets에 필수 API 키가 세팅되지 않았습니다!")
        st.stop()

@st.cache_data(ttl=3600)
def get_groq_models(api_key):
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        res = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
        data = res.json()
        return [m["id"] for m in data["data"] if "whisper" not in m["id"]]
    except:
        return ["llama-3.3-70b-versatile"]

@st.cache_data(ttl=3600)
def get_gemini_models(api_key):
    try:
        res = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}")
        data = res.json()
        return [m["name"] for m in data["models"] if "generateContent" in m.get("supportedGenerationMethods", [])]
    except:
        return ["models/gemini-1.5-flash"]

# 📌 신규 추가: 노션에 있는 모든 데이터베이스 리스트를 긁어옵니다!
@st.cache_data(ttl=300)
def get_notion_databases(api_key):
    if not api_key: return {}
    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {"filter": {"value": "database", "property": "object"}}
    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            results = res.json().get("results", [])
            db_dict = {}
            for db in results:
                title_objs = db.get("title", [])
                title = title_objs[0].get("plain_text", "제목 없음") if title_objs else "제목 없음"
                db_dict[f"📁 {title}"] = db['id'] # 화면엔 제목표시, 뒤로는 ID 저장
            return db_dict
        return {}
    except:
        return {}
