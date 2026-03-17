import streamlit as st
import json
import os
import time
import subprocess # 📌 백그라운드 워커 실행용
import sys        # 📌 현재 파이썬 환경 확인용
import google.generativeai as genai
from api_setup import get_secrets, get_groq_models, get_gemini_models, get_notion_databases
from discord_bot import report_to_discord
from agent import LobsterAgent
import database 

st.set_page_config(page_title="Lobster Chat Center", page_icon="🦞", layout="wide")

database.init_db()
secrets = get_secrets()
groq_models = get_groq_models(secrets["GROQ"])
gemini_models = get_gemini_models(secrets["GEMINI"])
default_groq = groq_models[0] if groq_models else "llama3-8b-8192"

AVAILABLE_TOOLS = [
    "🦆 무제한 웹검색 (무료)", 
    "🕷️ 웹페이지 읽기 (무료)", 
    "💾 로컬 파일 제어 (무료)", 
    "💻 파이썬 터미널 실행 (무료)",
    "📝 Notion API", 
    "💬 Slack API"
]

ROSTER_FILE = "agents_roster.json"
PID_FILE = "worker.pid" # 📌 워커 엔진 생사 확인용 파일

# 📌 워커 엔진 상태 체크 함수
def get_worker_pid():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read())
            os.kill(pid, 0) # 프로세스가 살아있는지 찔러봄
            return pid
        except:
            os.remove(PID_FILE) # 죽었으면 찌꺼기 파일 삭제
    return None

def load_roster():
    if os.path.exists(ROSTER_FILE):
        try:
            with open(ROSTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            roster = {}
            for key, info in data.items():
                agent = LobsterAgent(secrets["GROQ"], info["name"], info["role"])
                agent.model_groq = info.get("model_groq", default_groq)
                agent.tools = info.get("tools", [])
                agent.notion_db_id = info.get("notion_db_id", None)
                roster[key] = agent
            return roster
        except: pass
    return {}

def save_roster(roster):
    data = {}
    for key, agent in roster.items():
        data[key] = {
            "name": agent.name, "role": agent.role,
            "model_groq": getattr(agent, "model_groq", default_groq),
            "tools": getattr(agent, "tools", []),
            "notion_db_id": getattr(agent, "notion_db_id", None)
        }
    with open(ROSTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if "agent_roster" not in st.session_state:
    saved_roster = load_roster()
    if not saved_roster:
        default_agent = LobsterAgent(secrets["GROQ"], "랍스타-01", "만능 비서")
        default_agent.model_groq = default_groq
        saved_roster["랍스타-01 (만능 비서)"] = default_agent
        save_roster(saved_roster)
    st.session_state.agent_roster = saved_roster

with st.sidebar:
    st.header("🌐 Language / 공용어 설정")
    app_lang = st.radio("UI & Agent Language", ["한국어", "English"], horizontal=True, label_visibility="collapsed")

def t(ko, en): return ko if app_lang == "한국어" else en

st.title(t("🦞 랍스타 컨트롤 센터 (아포칼립스 군단)", "🦞 Lobster Chat Center (Apocalypse Legion)"))

# ==========================================
# 3. 사이드바 (요원 채용 및 서기 설정)
# ==========================================
with st.sidebar:
    st.divider()
    st.header(t("📝 수석 서기 설정 (Gemini)", "📝 Chief Secretary (Gemini)"))
    secretary_model = st.selectbox(t("최종 보고서 전담 모델", "Final Report Model"), gemini_models)
    
    st.divider()
    st.header(t("🦞 군단 인력소", "🦞 Agent Recruitment"))
    
    with st.expander(t("➕ 새 에이전트 채용 (무기 지급)", "➕ Hire New Agent (Assign Tools)")):
        new_name = st.text_input(t("이름", "Name (e.g., Jacob)"))
        new_role = st.text_input(t("직무", "Role (e.g., Project Manager)"))
        sel_groq = st.selectbox(t("🧠 사고력 및 실무 뇌 (Groq)", "🧠 Brain & Hands (Groq)"), groq_models)
        selected_tools = st.multiselect(t("🛠️ 툴 장착", "🛠️ Assign Tools"), AVAILABLE_TOOLS)
        
        selected_notion_db_id = None
        if "📝 Notion API" in selected_tools:
            notion_dbs = get_notion_databases(st.secrets.get("NOTION_API_KEY", ""))
            if notion_dbs:
                selected_db_name = st.selectbox(t("📂 담당할 노션 DB 선택", "📂 Select Notion DB"), list(notion_dbs.keys()))
                selected_notion_db_id = notion_dbs[selected_db_name]
        
        if st.button(t("채용 및 명부 등록 🚀", "Hire & Save 🚀")):
            if new_name and new_role:
                new_agent = LobsterAgent(secrets["GROQ"], new_name, new_role)
                new_agent.model_groq = sel_groq
                new_agent.tools = selected_tools
                new_agent.notion_db_id = selected_notion_db_id
                
                st.session_state.agent_roster[f"{new_name} ({new_role})"] = new_agent
                save_roster(st.session_state.agent_roster)
                st.success(t(f"🎉 '{new_name}' 채용 완료!", f"🎉 '{new_name}' Hired!"))
                time.sleep(1)
                st.rerun()

# ==========================================
# 4. 메인 화면: 탭 분리
# ==========================================
tab1_name = t("💬 1:1 개인 업무 지시", "💬 1:1 Direct Messages")
tab2_name = t("🔥 원탁 회의실", "🔥 War Room")
tab3_name = t("🏢 장기 프로젝트 사령부 (오픈클로 모드)", "🏢 Long-term Project HQ (OpenClo Mode)")
tab1, tab2, tab3 = st.tabs([tab1_name, tab2_name, tab3_name])

# ------------------------------------------
# [탭 1] 1:1 개인 업무 지시 (DM)
# ------------------------------------------
with tab1:
    contact_col, chat_col = st.columns([1, 3])
    with contact_col:
        st.subheader(t("👥 내 요원 목록", "👥 My Agents"))
        selected_agent_key = st.radio(t("업무 지시 요원 선택", "Select agent"), list(st.session_state.agent_roster.keys()), label_visibility="collapsed")
        active_lobster = st.session_state.agent_roster[selected_agent_key]
        st.divider()
        st.caption(t(f"🧠 장착 뇌:\n`{active_lobster.model_groq}`", f"🧠 Brain:\n`{active_lobster.model_groq}`"))
        tools_str = ", ".join(active_lobster.tools) if hasattr(active_lobster, 'tools') and active_lobster.tools else t("맨손 (툴 없음)", "No Tools")
        st.caption(t(f"🛠️ 장착 툴:\n{tools_str}", f"🛠️ Tools:\n{tools_str}"))
        
        if len(st.session_state.agent_roster) > 1:
            if st.button(t("🗑️ 요원 해고", "🗑️ Fire Agent"), use_container_width=True):
                del st.session_state.agent_roster[selected_agent_key]
                save_roster(st.session_state.agent_roster)
                st.rerun()

    with chat_col:
        st.subheader(f"💬 {active_lobster.name} {t('요원과의 DM', 'DM')}")
        chat_memory_key = f"dm_history_{selected_agent_key}"
        if chat_memory_key not in st.session_state:
            st.session_state[chat_memory_key] = [{"role": "assistant", "content": t("대기 중입니다! 🫡", "Awaiting orders! 🫡")}]

        uploaded_file = st.file_uploader(t(f"📁 분석 데이터 전달", f"📁 Upload File"), type=['txt', 'csv', 'md'], key=f"file_{selected_agent_key}")
        file_data = uploaded_file.getvalue().decode("utf-8") if uploaded_file else ""

        for msg in st.session_state[chat_memory_key]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        if prompt := st.chat_input(t("지시하기...", "Command..."), key=f"input_{selected_agent_key}"):
            full_prompt = prompt if not file_data else f"{prompt}\n\n[Data:\n{file_data}\n]"
            st.session_state[chat_memory_key].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner(t("실행 중... 🧠🛠️", "Executing... 🧠🛠️")):
                    try:
                        history_for_agent = [{"role": m["role"], "content": m["content"]} for m in st.session_state[chat_memory_key][-10:]]
                        action_type, text1, text2 = active_lobster.think_and_act(full_prompt, history_for_agent)
                        st.markdown(text1)
                        if action_type == "task": st.success(t("✅ 실무 작업 완료!", "✅ Task Executed!"))
                        final_memory = text1
                    except Exception as e:
                        final_memory = f"Error: {e}"
                st.session_state[chat_memory_key].append({"role": "assistant", "content": final_memory})

# ------------------------------------------
# [탭 2] 🔥 원탁 회의실 (끝장 토론)
# ------------------------------------------
with tab2:
    st.subheader(t("토론 참석자 세팅", "Select Attendees"))
    attendees_keys = st.multiselect(t("회의 참석 에이전트 호출", "Call agents"), list(st.session_state.agent_roster.keys()), key="meeting_attendees_widget", label_visibility="collapsed")
    st.divider()

    if "is_debating" not in st.session_state: st.session_state.is_debating = False

    col_start, col_stop = st.columns([3, 1])
    with col_start:
        if not st.session_state.is_debating:
            agenda_input = st.text_input(t("회의 안건 던지기...", "Agenda..."), key="agenda_input")
            if st.button(t("🔥 아포칼립스 끝장 토론 시작!", "🔥 Start Apocalypse Debate!"), use_container_width=True):
                if len(attendees_keys) < 2: st.warning(t("최소 2명 필요!", "Need 2+ attendees!"))
                elif not agenda_input: st.warning(t("안건을 입력해주세요!", "Please enter agenda!"))
                else:
                    st.session_state.is_debating = True
                    st.session_state.meeting_agenda = agenda_input
                    st.session_state.active_attendees = attendees_keys 
                    st.session_state.turn_index = 0
                    st.session_state.compressed_memory = "" 
                    st.session_state.short_term_memory = [] 
                    
                    apoc_kr = f"사령관 안건: '{agenda_input}'\n1. 무조건 '{app_lang}'로만 말해라.\n2. 5문장 이내 핵심만.\n3. 비판하고 극단적 아이디어 도출.\n4. 완벽한 합의 시에만 [결론] 추가.\n5. [TASK] 태그 금지."
                    apoc_en = f"Agenda: '{agenda_input}'\n1. Speak ONLY in '{app_lang}'.\n2. Max 5 sentences.\n3. Criticize & be extreme.\n4. Append [결론] ONLY when agreed.\n5. NO [TASK] tag."
                    
                    st.session_state.meeting_history_ui = [{"role": "user", "content": t(apoc_kr, apoc_en)}]
                    st.session_state.full_meeting_log = f"**[Agenda]** {agenda_input}\n\n"
                    st.rerun()

    with col_stop:
        if st.session_state.is_debating:
            if st.button(t("🛑 강제 중지", "🛑 Stop Debate"), type="primary", use_container_width=True):
                st.session_state.is_debating = False
                st.rerun()

    st.divider()

    if "meeting_history_ui" in st.session_state and len(st.session_state.meeting_history_ui) > 1:
        for msg in st.session_state.meeting_history_ui[1:]:
            with st.chat_message("assistant" if "발언" in msg["content"] or "Speaker" in msg["content"] else "user"):
                st.markdown(msg["content"].replace("[결론]", ""))

    if st.session_state.is_debating:
        attendees = st.session_state.active_attendees 
        current_key = attendees[st.session_state.turn_index % len(attendees)]
        current_agent = st.session_state.agent_roster[current_key]
        
        if st.session_state.turn_index > 0:
            timer_ph = st.empty()
            for sec in range(20, 0, -1):
                timer_ph.info(t(f"⏳ 과열 방지 중... {current_agent.name} 발언까지 **{sec}초** 대기", f"⏳ Cooling down... {sec}s"))
                time.sleep(1)
            timer_ph.empty()

        with st.chat_message("assistant"):
            if len(st.session_state.short_term_memory) > 4:
                old1 = st.session_state.short_term_memory.pop(0)
                old2 = st.session_state.short_term_memory.pop(0)
                with st.spinner(t("🧠 과거 기억 압축 중...", "🧠 Compressing memories...")):
                    try:
                        sum_res = current_agent.groq_client.chat.completions.create(
                            messages=[{"role": "user", "content": f"Summarize this in '{app_lang}' into 3 sentences. Previous: {st.session_state.compressed_memory}. New: {old1['content']} \n {old2['content']}"}],
                            model="llama3-8b-8192", temperature=0.2
                        )
                        st.session_state.compressed_memory = sum_res.choices[0].message.content
                    except: pass

            groq_context = [{"role": "user", "content": st.session_state.meeting_history_ui[0]["content"]}]
            if st.session_state.compressed_memory:
                groq_context.append({"role": "user", "content": f"[Memory]\n{st.session_state.compressed_memory}"})
            groq_context.extend(st.session_state.short_term_memory)

            with st.spinner(t(f"🎤 {current_agent.name} 발언 준비 중...", f"🎤 {current_agent.name} is thinking...")):
                try:
                    action, reply, _ = current_agent.think_and_act(
                        t(f"너의 차례다. '{app_lang}'로 5문장 이내로 말해. 결론이 났다면 [결론]을 적어.", f"Your turn. Speak in '{app_lang}' under 5 sentences. If concluded, append [결론]."),
                        groq_context
                    )
                    
                    if "[결론]" in reply and st.session_state.turn_index < len(attendees) * 2:
                        reply = reply.replace("[결론]", t(f"\n\n**(사령관: \"장난해? 더 파고들어!\")**", f"\n\n**(Commander: \"Not enough! Dig deeper!\")**"))
                    
                    st.markdown(f"**{current_agent.name} ({current_agent.role})**\n{reply}")
                    
                    log_entry = {"role": "assistant", "content": f"[{current_agent.name}]: {reply}"}
                    st.session_state.meeting_history_ui.append(log_entry)
                    st.session_state.short_term_memory.append(log_entry)
                    st.session_state.full_meeting_log += f"**[{current_agent.name}]**\n{reply}\n\n"
                    
                    if "[결론]" in reply:
                        st.session_state.is_debating = False
                        st.success(t("✅ 합의 도달! 최종 보고서를 작성합니다...", "✅ Agreement Reached! Generating Final Report..."))
                        
                        with st.spinner(t("수석 서기(Gemini)가 직무 맞춤형 액션 아이템을 정리 중입니다... 📝", "Chief Secretary (Gemini) is finalizing... 📝")):
                            try:
                                genai.configure(api_key=secrets["GEMINI"])
                                summary_model = genai.GenerativeModel(secretary_model)
                                attendees_info_list = [f"- {st.session_state.agent_roster[k].name} (직무/Role: {st.session_state.agent_roster[k].role})" for k in attendees]
                                attendees_info_str = "\n".join(attendees_info_list)
                                
                                report_prompt = f"""
                                다음은 방금 완료된 회의의 전체 기록이다. 모든 내용을 반드시 '{app_lang}'로 작성해라.
                                [안건 / Agenda]: {st.session_state.meeting_agenda}
                                [참여 요원 및 직무 / Attendees & Roles]: \n{attendees_info_str}
                                [전체 회의록 / Full Meeting Log]: \n{st.session_state.full_meeting_log}
                                
                                다음 양식에 맞춰 완벽한 마크다운 형식의 최종 회의 결과 보고서를 작성해라:
                                1. 📌 미팅 요약 (Meeting Summary)
                                2. 💡 중요 내용 (Key Takeaways)
                                3. 📅 액션 아이템 (Action Items - 직무에 완벽하게 일치하는 업무만 배정할 것!)
                                4. 🎯 기대 효과 (Expected Results)
                                5. 🤖 각 에이전트별 개인 업무 AI 프롬프트 (Individual AI Prompts - 1:1 대화방 복붙용 1인칭 명령조)
                                """
                                final_report = summary_model.generate_content(report_prompt).text
                                st.session_state.final_report = final_report
                                report_to_discord(secrets["DISCORD"], "📜 최종 회의 보고서", final_report[:4000], 15158332)
                            except Exception as e:
                                st.session_state.final_report = f"요약 생성 중 에러 발생: {e}"
                        st.rerun()
                    else:
                        st.session_state.turn_index += 1
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state.is_debating = False

    if not st.session_state.is_debating and "final_report" in st.session_state:
        st.divider()
        st.subheader(t("📜 수석 서기(Gemini)의 최종 회의 보고서", "📜 Final Meeting Report by Chief Secretary (Gemini)"))
        with st.container(border=True):
            st.markdown(st.session_state.final_report)

# ------------------------------------------
# [탭 3] 🏢 장기 프로젝트 사령부 (오픈클로 모드 CCTV)
# ------------------------------------------
with tab3:
    # 📌 1. 서버 엔진 컨트롤 패널
    st.subheader(t("⚙️ 지하실 워커(Worker) 엔진 컨트롤", "⚙️ Background Worker Engine Control"))
    
    current_pid = get_worker_pid()
    
    col_status, col_btn = st.columns([3, 1])
    with col_status:
        if current_pid:
            st.success(t(f"🟢 워커 엔진이 백그라운드에서 가동 중입니다. (PID: {current_pid})", f"🟢 Worker engine is running. (PID: {current_pid})"))
            st.caption(t("사령관님이 웹 브라우저를 닫아도 워커는 알아서 24시간 일합니다!", "Worker will keep running 24/7 even if you close the browser!"))
        else:
            st.error(t("🔴 워커 엔진이 꺼져 있습니다. 프로젝트를 자동 실행하려면 엔진을 먼저 켜주세요.", "🔴 Worker engine is OFF. Start the engine to run projects."))
            
    with col_btn:
        if current_pid:
            if st.button(t("⏹️ 워커 정지", "⏹️ Stop Worker"), use_container_width=True):
                try:
                    import signal
                    os.kill(current_pid, signal.SIGTERM) 
                    os.remove(PID_FILE)
                except Exception as e:
                    st.warning(f"종료 실패 (이미 꺼져있을 수 있습니다): {e}")
                    if os.path.exists(PID_FILE): os.remove(PID_FILE)
                st.rerun()
        else:
            if st.button(t("▶️ 워커 가동", "▶️ Start Worker"), type="primary", use_container_width=True):
                p = subprocess.Popen([sys.executable, "worker.py"])
                with open(PID_FILE, "w") as f:
                    f.write(str(p.pid))
                st.rerun()

    st.divider()

    # 📌 2. 장기 프로젝트 하달 구역
    st.subheader(t("👑 장기 프로젝트 백그라운드 지시", "👑 Assign Background Project"))
    
    col_l, col_w = st.columns(2)
    with col_l:
        leader_key = st.selectbox(t("👑 총괄 리더 (PM) 선택", "👑 Select Project Leader"), list(st.session_state.agent_roster.keys()), key="auto_leader")
    with col_w:
        worker_keys = st.multiselect(t("👷 실무 요원 선택 (다중 선택)", "👷 Select Workers"), list(st.session_state.agent_roster.keys()), key="auto_workers")
    
    grand_goal = st.text_area(t("🚀 장기 프로젝트 마스터 플랜 (사령관의 목표)", "🚀 Grand Project Goal"), height=100)
    
    if st.button(t("📥 우체통에 명령서 넣기 (DB 저장)", "📥 Dispatch Order to Worker!"), use_container_width=True):
        if not current_pid: st.warning(t("⚠️ 위에 있는 엔진 전원을 먼저 켜주세요!", "⚠️ Turn on the engine above first!"))
        elif not worker_keys: st.warning(t("실무 요원이 최소 1명 필요합니다!", "Need at least 1 worker!"))
        elif not grand_goal: st.warning(t("프로젝트 목표를 입력하세요!", "Enter project goal!"))
        else:
            database.create_job(leader_key, worker_keys, grand_goal)
            st.success(t("✅ 명령이 우체통(DB)에 저장되었습니다! 워커가 곧 낚아채서 실행합니다.", "✅ Job saved in DB! Worker will pick it up soon."))
            st.balloons()
            time.sleep(1.5)
            st.rerun()

    st.divider()

    # 📌 3. 실시간 CCTV 모니터링 구역 (HITL 피드백 주입 포함)
    col_dash, col_ref = st.columns([4, 1])
    with col_dash:
        st.subheader(t("📡 지하실 작업 현황판 (CCTV)", "📡 Underground Worker CCTV"))
    with col_ref:
        if st.button("🔄 새로고침 (Refresh)", use_container_width=True):
            st.rerun()

    jobs = database.get_all_jobs()
    if not jobs:
        st.info("현재 대기 중이거나 진행 중인 장기 프로젝트가 없습니다.")
    else:
        for job in jobs:
            job_id, leader, workers_json, goal, status, logs, created_at = job
            workers = json.loads(workers_json)
            
            status_color = "🟢" if status == "COMPLETED" else "🟡" if status == "RUNNING" else "🔴" if status == "FAILED" else "🛑" if status == "PAUSED" else "⚪"
            
            with st.expander(f"{status_color} [Job #{job_id}] {goal[:30]}... ({status}) - {created_at}", expanded=(status=="PAUSED")):
                st.caption(f"**👑 리더:** {leader} | **👷 실무자:** {', '.join(workers)}")
                st.write(f"**목표:** {goal}")
                st.markdown("---")
                st.markdown("**📜 실시간 작업 로그**")
                st.code(logs, language="markdown")
                
                # 📌 신규: 작업이 일시 정지(PAUSED) 되었을 때 나타나는 구명조끼 UI
                if status == "PAUSED":
                    st.error("🚨 에이전트가 사령관님의 도움을 요청했습니다! (위 로그의 SOS 메시지를 확인하세요)")
                    feedback = st.text_input("사령관의 지시 및 정보 제공 (예: '이메일 주소는 abc@gmail.com이야', '해당 작업은 빼고 진행해')", key=f"fb_{job_id}")
                    if st.button("▶️ 피드백 전송 및 작업 재개", key=f"btn_{job_id}", type="primary", use_container_width=True):
                        if feedback:
                            database.provide_feedback(job_id, feedback)
                            st.success("✅ 명령이 하달되었습니다. 워커가 곧 처음부터 작업을 재개합니다!")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.warning("정보를 입력해주세요!")
