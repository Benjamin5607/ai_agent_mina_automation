import requests
import streamlit as st

def report_to_discord(webhook_url, title, description, color=16730698):
    """디스코드 웹후크 전송 전담 함수"""
    payload = {
        "username": "랍스타-시스템",
        "avatar_url": "https://i.imgur.com/4E7989q.png",
        "embeds": [{"title": title, "description": description, "color": color}]
    }
    try:
        requests.post(webhook_url, json=payload)
    except Exception as e:
        st.toast(f"디스코드 전송 실패: {e}")
