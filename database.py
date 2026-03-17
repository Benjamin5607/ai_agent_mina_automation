import sqlite3
import json

DB_NAME = "lobster_jobs.db"

def init_db():
    """DB가 없으면 최초 생성합니다."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            leader TEXT,
            workers TEXT,
            grand_goal TEXT,
            status TEXT,
            logs TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def create_job(leader, workers, grand_goal):
    """사령관님이 새 임무를 내리면 우체통에 'PENDING(대기중)' 상태로 꽂아넣습니다."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO jobs (leader, workers, grand_goal, status, logs) VALUES (?, ?, ?, ?, ?)",
              (leader, json.dumps(workers), grand_goal, "PENDING", "📥 [시스템] 사령관님의 장기 프로젝트 지시가 접수되었습니다. (워커 대기 중...)\n"))
    conn.commit()
    conn.close()

def get_all_jobs():
    """대시보드에 띄울 모든 작업 목록을 가져옵니다."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, leader, workers, grand_goal, status, logs, created_at FROM jobs ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows
