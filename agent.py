from groq import Groq
import streamlit as st
import tools

class LobsterAgent:
    def __init__(self, groq_key, name="랍스타-01", role="만능 비서"):
        self.name = name
        self.role = role
        self.groq_client = Groq(api_key=groq_key)
        self.tools = []
        self.notion_db_id = None
        self.model_groq = "llama3-8b-8192"

    def execute_tools(self, execution_plan, actual_content, api_secrets):
        action_logs = []
        def extract_keyword(prompt_text):
            try:
                res = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt_text}],
                    model="llama3-8b-8192", temperature=0.1
                )
                return res.choices[0].message.content.replace('"', '').strip()
            except: return ""

        if "🌐 Web Crawler" in self.tools and ("웹" in execution_plan or "크롤링" in execution_plan):
            query = extract_keyword(f"Extract ONE english keyword for search: {execution_plan}")
            result = tools.use_web_crawler(query, api_secrets.get("TAVILY_API_KEY", ""))
            action_logs.append(result)
        if "🎨 Pixabay API" in self.tools and ("이미지" in execution_plan or "사진" in execution_plan):
            query = extract_keyword(f"Extract ONE english keyword for image: {execution_plan}")
            result = tools.use_pixabay_api(query, api_secrets.get("PIXABAY_API_KEY", ""))
            action_logs.append(result)
        if "📝 Notion API" in self.tools and ("노션" in execution_plan or "문서" in execution_plan):
            title = f"[{self.name}] 결과 보고"
            db_to_use = self.notion_db_id if self.notion_db_id else api_secrets.get("NOTION_DATABASE_ID", "")
            result = tools.use_notion_api(title, actual_content, api_secrets.get("NOTION_API_KEY", ""), db_to_use)
            action_logs.append(result)
        if "💬 Slack API" in self.tools and ("슬랙" in execution_plan or "알림" in execution_plan):
            result = tools.use_slack_api(f"[{self.name}] {actual_content[:200]}...", api_secrets.get("SLACK_BOT_TOKEN", ""))
            action_logs.append(result)
            
        return "\n\n".join(action_logs) if action_logs else "⚠️ 툴 조건에 맞지 않아 실행하지 않았습니다."

    def think_and_act(self, user_message, chat_history):
        # 📌 1. 무기 목록을 더 명확하게 못 박습니다.
        if not self.tools:
            tools_info = "현재 장착된 물리적 무기가 전혀 없습니다. (소프트웨어 연동, API 호출, 이메일 발송 등 물리적 행동 100% 불가)"
        else:
            tools_info = f"현재 장착된 물리적 무기: {', '.join(self.tools)}. (이 목록에 없는 Jira, GitHub, 이메일, 데이터베이스 생성 등은 절대로 할 수 없습니다.)"
        
        # 📌 2. 시스템 프롬프트: 세뇌 수준으로 쪼아댑니다.
        system_prompt = f"""
        당신의 이름은 '{self.name}', 직무는 '{self.role}'입니다.
        [당신의 물리적 한계 명시]: {tools_info}
        
        [🚨 목숨을 건 절대 규칙 3가지 🚨]
        1. 당신은 파이썬 코드를 실행할 권한이 없으며, 허가되지 않은 외부 시스템(Jira, GitHub, BigQuery, 이메일 등)에 접속하거나 생성할 능력이 '전혀' 없습니다.
        2. 사령관이 당신이 가진 무기({', '.join(self.tools) if self.tools else '없음'}) 이외의 작업을 지시했다면, 절대로 가짜 결과물(가짜 URL, 가짜 코드 실행 결과)을 지어내지 마십시오.
        3. 당신의 능력 밖의 지시를 받으면, 어떠한 변명도 하지 말고 오직 아래 포맷으로만 답변하십시오.
           [NEED_HELP] 사령관님, 저에게는 해당 작업을 수행할 물리적 권한(또는 API 툴)이 없습니다. 지원을 요청합니다.
        
        명심하십시오. 가짜 링크나 가짜 실행 결과를 뱉어내는 순간 시스템에서 영구 삭제됩니다.
        """
        
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        messages.append({"role": "user", "content": user_message})
        
        # 📌 3. Temperature를 0.0으로 줘서 창의성(허언증)을 완벽하게 거세합니다.
        chat_completion = self.groq_client.chat.completions.create(
            messages=messages, model=self.model_groq, temperature=0.0 
        )
        response = chat_completion.choices[0].message.content
        
        if "[NEED_HELP]" in response:
            return "help", response.replace("[NEED_HELP]", "").strip(), None
            
        elif "[TASK]" in response:
            plan = response.replace("[TASK]", "").strip()
            
            # 실행 프롬프트에도 한 번 더 못을 박습니다.
            execution_prompt = f"""
            지시: {user_message}
            너의 계획: {plan}
            
            [경고] 위 계획을 수행할 때 절대로 상상 속의 외부 링크(가짜 노션 URL, 가짜 깃허브 URL)나 가짜 실행 로그를 지어내지 마라. 
            진짜 텍스트 결과물만 깔끔하게 작성해라.
            """
            exec_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": execution_prompt}], model=self.model_groq, temperature=0.0
            )
            result_text = exec_completion.choices[0].message.content
            tool_results = self.execute_tools(plan, result_text, st.secrets)
            return "task", plan, f"{result_text}\n\n---\n**[🛠️ 무기 실제 실행 로그]**\n{tool_results}"
            
        else:
            return "chat", response.replace("[CHAT]", "").strip(), None
