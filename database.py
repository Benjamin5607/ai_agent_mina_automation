import sqlite3
import json

DB_NAME = "lobster_jobs.db"

def init_db():
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
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO jobs (leader, workers, grand_goal, status, logs) VALUES (?, ?, ?, ?, ?)",
              (leader, json.dumps(workers), grand_goal, "PENDING", "📥 [시스템] 사령관님의 장기 프로젝트가 접수되었습니다.\n"))
    conn.commit()
    conn.close()

def get_all_jobs():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, leader, workers, grand_goal, status, logs, created_at FROM jobs ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

# 📌 신규: 사령관님의 긴급 개입(HITL) 함수!
def provide_feedback(job_id, feedback):
    """사령관님이 제공한 추가 정보/명령을 목표에 덧붙이고, 다시 PENDING(대기) 상태로 돌립니다."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT grand_goal, logs FROM jobs WHERE id=?", (job_id,))
    row = c.fetchone()
    if row:
        new_goal = row[0] + f"\n\n[🚨 사령관의 긴급 추가 정보/지시]: {feedback}"
        new_logs = row[1] + f"\n\n🦸‍♂️ [사령관 개입 완료]: {feedback}\n🔄 작업을 처음부터 재개합니다...\n"
        c.execute("UPDATE jobs SET grand_goal=?, logs=?, status=? WHERE id=?", (new_goal, new_logs, "PENDING", job_id))
    conn.commit()
    conn.close()

def delete_job(job_id):
    """사령관의 권한으로 프로젝트를 영구 삭제합니다."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    conn.commit()
    conn.close()
