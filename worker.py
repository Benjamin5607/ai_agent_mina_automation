import sqlite3
import json
import time
import traceback
from api_setup import get_secrets
from discord_bot import report_to_discord
from agent import LobsterAgent

DB_NAME = "lobster_jobs.db"
ROSTER_FILE = "agents_roster.json"

def log_to_db(job_id, new_log):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT logs FROM jobs WHERE id=?", (job_id,))
    current_logs = c.fetchone()[0]
    updated_logs = current_logs + f"\n{new_log}"
    c.execute("UPDATE jobs SET logs=? WHERE id=?", (updated_logs, job_id))
    conn.commit()
    conn.close()
    print(new_log)

def set_job_status(job_id, status):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()
    conn.close()

def load_agents():
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
    except: return {}

def main():
    print("=====================================================")
    print("🛠️ HITL 워커(Worker) 가동! (거짓말 차단 및 구조요청 모드)")
    print("=====================================================")
    secrets = get_secrets()
    
    while True:
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT id, leader, workers, grand_goal FROM jobs WHERE status='PENDING' ORDER BY id ASC LIMIT 1")
            job = c.fetchone()
            conn.close()

            if not job:
                time.sleep(5)
                continue

            job_id, leader_key, workers_json, grand_goal = job
            worker_keys = json.loads(workers_json)
            
            set_job_status(job_id, "RUNNING")
            log_to_db(job_id, f"\n🏃‍♂️ [Job #{job_id}] 작업 시작! (총괄 리더: {leader_key})")
            roster = load_agents()
            leader_agent = roster.get(leader_key)
            
            if not leader_agent:
                set_job_status(job_id, "FAILED")
                continue

            # Step 1: Planning
            log_to_db(job_id, "\n**[Step 1: 리더의 업무 분배]**")
            workers_info = "\n".join([f"- {roster[k].name} ({roster[k].role}) [보유 툴: {','.join(roster[k].tools)}]" for k in worker_keys if k in roster])
            plan_prompt = f"목표: {grand_goal}\n명단 및 보유 툴:\n{workers_info}\n위 실무자들이 '보유한 툴'로만 할 수 있는 현실적인 업무만 지시해라.\n양식: [작업자이름] | [지시내용]"
            
            action, reply, _ = leader_agent.think_and_act(plan_prompt, [])
            if action == "help": # 📌 리더가 SOS 친 경우!
                log_to_db(job_id, f"🛑 [리더 SOS 요청! 작업 중단]: {reply}")
                set_job_status(job_id, "PAUSED")
                continue
                
            task_list = [t for t in reply.split('\n') if "|" in t]
            log_to_db(job_id, "\n".join([f"📋 {t}" for t in task_list]))

            # Step 2: Executing
            log_to_db(job_id, "\n**[Step 2: 실무 요원 실행]**")
            task_results = []
            needs_help = False
            
            for current_task in task_list:
                worker_name, task_detail = current_task.split("|")[0].strip(), current_task.split("|")[1].strip()
                worker_agent = next((roster[k] for k in worker_keys if k in roster and roster[k].name in worker_name), None)
                
                if worker_agent:
                    time.sleep(20) # 쿨타임
                    log_to_db(job_id, f"⚙️ [{worker_agent.name}] 작업 중...")
                    w_action, w_reply, w_final = worker_agent.think_and_act(f"지시: {task_detail}\n[명령] 할 수 없으면 [NEED_HELP]를 외쳐라.", [])
                    
                    if w_action == "help": # 📌 실무자가 SOS 친 경우!
                        log_to_db(job_id, f"🛑 [{worker_agent.name}의 SOS! 작업 일시 정지]\n{w_reply}")
                        needs_help = True
                        break # 릴레이 즉시 파기
                    else:
                        res_text = w_final if w_final else w_reply
                        task_results.append(f"[{worker_agent.name}]\n{res_text}")
                        log_to_db(job_id, f"✅ [{worker_agent.name} 완료]\n{res_text[:100]}...\n")
            
            if needs_help:
                set_job_status(job_id, "PAUSED")
                continue # 다음 job으로 넘어감

            # Step 3: Review
            log_to_db(job_id, "\n**[Step 3: 리더 최종 취합]**")
            time.sleep(20)
            r_action, r_reply, r_final = leader_agent.think_and_act(f"목표: {grand_goal}\n결과: {''.join(task_results)}\n최종 보고서를 써라. (할 수 없으면 [NEED_HELP])", [])
            
            if r_action == "help":
                log_to_db(job_id, f"🛑 [리더 SOS! 작업 중단]: {r_reply}")
                set_job_status(job_id, "PAUSED")
                continue

            report = r_final if r_final else r_reply
            log_to_db(job_id, f"👑 [최종 보고서]\n{report}")
            report_to_discord(secrets["DISCORD"], "🚀 프로젝트 완료!", report[:4000], 15158332)
            set_job_status(job_id, "COMPLETED")
            log_to_db(job_id, "\n🎉 모든 작업 종료.")
            
        except Exception as e:
            log_to_db(job_id, f"\n🚨 시스템 에러: {e}\n{traceback.format_exc()}")
            set_job_status(job_id, "FAILED")
        
        time.sleep(5)

if __name__ == "__main__":
    main()
