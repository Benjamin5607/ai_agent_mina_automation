import sqlite3
import json
import time
import traceback
import streamlit as st # st.secrets를 쓰기 위해 임포트
from api_setup import get_secrets
from discord_bot import report_to_discord
from agent import LobsterAgent

DB_NAME = "lobster_jobs.db"
ROSTER_FILE = "agents_roster.json"

def log_to_db(job_id, new_log):
    """우체통(DB)의 기존 로그에 새로운 진행 상황을 덧붙입니다. (CCTV용)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT logs FROM jobs WHERE id=?", (job_id,))
    current_logs = c.fetchone()[0]
    updated_logs = current_logs + f"\n{new_log}"
    c.execute("UPDATE jobs SET logs=? WHERE id=?", (updated_logs, job_id))
    conn.commit()
    conn.close()
    print(new_log) # 터미널 창에도 띄워줍니다!

def set_job_status(job_id, status):
    """작업 상태를 변경합니다 (PENDING -> RUNNING -> COMPLETED/FAILED)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()
    conn.close()

def load_agents():
    """워커가 스스로 직원 명부를 확인합니다."""
    secrets = get_secrets()
    try:
        with open(ROSTER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        roster = {}
        for key, info in data.items():
            agent = LobsterAgent(secrets["GROQ"], info["name"], info["role"])
            agent.model_groq = info.get("model_groq", "llama3-8b-8192")
            agent.tools = info.get("tools", [])
            agent.notion_db_id = info.get("notion_db_id", None)
            roster[key] = agent
        return roster
    except Exception as e:
        print(f"명부 로드 실패: {e}")
        return {}

def main():
    print("=====================================================")
    print("🛠️ 지하실 워커(Worker) 가동 시작! (24시간 무한 대기 모드)")
    print("사령관님의 명령을 기다립니다...")
    print("=====================================================")
    
    secrets = get_secrets()
    
    # 📌 무한 루프: 절대 죽지 않고 5초마다 우체통을 확인합니다!
    while True:
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            # 가장 오래된 '대기 중(PENDING)' 일감을 하나 꺼냅니다.
            c.execute("SELECT id, leader, workers, grand_goal FROM jobs WHERE status='PENDING' ORDER BY id ASC LIMIT 1")
            job = c.fetchone()
            conn.close()

            if not job:
                time.sleep(5) # 일감이 없으면 5초 쉬고 다시 확인
                continue

            job_id, leader_key, workers_json, grand_goal = job
            worker_keys = json.loads(workers_json)
            
            set_job_status(job_id, "RUNNING")
            log_to_db(job_id, f"\n🏃‍♂️ [Job #{job_id}] 작업 시작! (총괄 리더: {leader_key})")

            roster = load_agents()
            leader_agent = roster.get(leader_key)
            
            if not leader_agent:
                log_to_db(job_id, "🚨 에러: 리더 에이전트를 찾을 수 없습니다. (해고되었거나 이름이 변경됨)")
                set_job_status(job_id, "FAILED")
                continue

            # -----------------------------------------------------
            # [Step 1] 리더의 업무 분배
            # -----------------------------------------------------
            log_to_db(job_id, "\n**[Step 1: 리더의 업무 분배 중...]**")
            workers_info = "\n".join([f"- {roster[k].name} ({roster[k].role})" for k in worker_keys if k in roster])
            plan_prompt = f"""
            사령관의 장기 프로젝트 목표: {grand_goal}
            당신은 이 프로젝트의 총괄 리더다. 다음 실무자들의 직무를 파악하고, 각자 해야 할 구체적인 업무(Task)를 지시해라.
            [실무자 명단]:\n{workers_info}\n
            결과는 반드시 아래 양식으로만 내뱉어라 (다른 말 금지):
            [작업자이름1] | [해야할 업무 구체적 지시]
            [작업자이름2] | [해야할 업무 구체적 지시]
            """
            
            res = leader_agent.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": plan_prompt}],
                model=leader_agent.model_groq, temperature=0.3
            )
            raw_tasks = res.choices[0].message.content.split('\n')
            task_list = [t for t in raw_tasks if "|" in t]
            log_to_db(job_id, "\n".join([f"📋 {t}" for t in task_list]))

            # -----------------------------------------------------
            # [Step 2] 실무 요원들의 업무 실행
            # -----------------------------------------------------
            log_to_db(job_id, "\n**[Step 2: 실무 요원 릴레이 업무 실행]**")
            task_results = []
            for current_task in task_list:
                worker_name = current_task.split("|")[0].strip()
                task_detail = current_task.split("|")[1].strip()
                
                worker_agent = None
                for k in worker_keys:
                    if k in roster and roster[k].name in worker_name:
                        worker_agent = roster[k]
                        break
                
                if worker_agent:
                    log_to_db(job_id, f"\n⏳ [{worker_agent.name}] 가동 준비 (API 과부하 방지 20초 대기 중...)")
                    time.sleep(20) # 📌 Groq API 429 방어용 쿨타임!
                    
                    log_to_db(job_id, f"⚙️ [{worker_agent.name}] 작업 중: {task_detail}")
                    action, reply, _ = worker_agent.think_and_act(
                        f"리더의 지시: {task_detail}\n[명령] 반드시 [TASK] 태그를 달고, 툴을 활용해서 완벽하게 결과물을 내라.", []
                    )
                    task_results.append(f"[{worker_agent.name} 결과]\n{reply}")
                    log_to_db(job_id, f"✅ [{worker_agent.name} 실행 결과]\n{reply}\n")
                else:
                    log_to_db(job_id, f"⚠️ '{worker_name}' 요원을 찾을 수 없어 건너뜁니다.")

            # -----------------------------------------------------
            # [Step 3] 리더의 최종 취합 및 리뷰
            # -----------------------------------------------------
            log_to_db(job_id, "\n**[Step 3: 리더 최종 취합 및 보고서 작성]**")
            all_results = "\n\n".join(task_results)
            review_prompt = f"""
            사령관의 목표: {grand_goal}
            요원들의 실행 결과: {all_results}
            당신은 리더다. 위 결과들을 종합하여 사령관님께 보고할 최종 요약 보고서를 작성해라. 문서화 툴이 있다면 [TASK] 태그를 달아 노션에 업로드해라.
            """
            
            log_to_db(job_id, "⏳ 리더 가동 준비 (API 과부하 방지 20초 대기 중...)")
            time.sleep(20)
            
            action, reply, _ = leader_agent.think_and_act(review_prompt, [])
            
            log_to_db(job_id, f"👑 [리더의 최종 보고서]\n{reply}")
            report_to_discord(secrets["DISCORD"], f"🚀 장기 프로젝트 [Job #{job_id}] 자동화 완료!", reply[:4000], 15158332)
            
            set_job_status(job_id, "COMPLETED")
            log_to_db(job_id, f"\n🎉 [Job #{job_id}] 모든 작업이 성공적으로 종료되었습니다.")
            
        except Exception as e:
            error_trace = traceback.format_exc()
            log_to_db(job_id, f"\n🚨 치명적 오류 발생: {e}\n```\n{error_trace}\n```")
            set_job_status(job_id, "FAILED")
            try:
                report_to_discord(secrets.get("DISCORD", ""), f"🚨 장기 프로젝트 실패!", f"에러: {e}", 16711680)
            except: pass

        time.sleep(5) # 한 사이클 돌고 혹시 모를 다음 일감 위해 5초 대기

if __name__ == "__main__":
    main()
