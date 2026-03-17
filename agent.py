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
        tools_info = ", ".join(self.tools) if self.tools else "없음(무기가 없으므로 물리적 작업 절대 불가)"
        
        # 📌 거짓말 즉결처형 및 [NEED_HELP] SOS 태그 도입!
        system_prompt = f"""
        너의 이름은 '{self.name}', 직무는 '{self.role}'이다.
        [현재 네가 장착한 물리적 무기(Tools)]: {tools_info}
        
        [🚨 사형 선고 규칙 - 반드시 지켜라 🚨]
        1. 너는 상상 속의 툴(이메일 전송, 깃허브 조작, 비정상 API 등)을 사용할 수 없다. 
        2. 네가 가진 무기({tools_info}) 외의 작업을 지시받았거나, 작업을 수행할 권한/정보(예: 이메일 주소, 대상 URL)가 없다면 절대 소설을 쓰지 마라.
        3. 불가능하다고 판단되는 즉시 맨 앞에 [NEED_HELP] 태그를 달고 "사령관님, ~가 없어서 진행할 수 없습니다. ~를 주십시오." 라고 SOS를 쳐라.
        4. 네가 가진 무기로 '진짜' 실행할 수 있을 때만 맨 앞에 [TASK] 태그를 달고 계획을 적어라.
        """
        
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        messages.append({"role": "user", "content": user_message})
        
        chat_completion = self.groq_client.chat.completions.create(
            messages=messages, model=self.model_groq, temperature=0.1 # 온도 낮춰서 허언증 원천봉쇄
        )
        response = chat_completion.choices[0].message.content
        
        # 📌 SOS를 치면 즉시 반환하여 시스템을 멈춥니다.
        if "[NEED_HELP]" in response:
            return "help", response.replace("[NEED_HELP]", "").strip(), None
            
        elif "[TASK]" in response:
            plan = response.replace("[TASK]", "").strip()
            execution_prompt = f"지시: {user_message}\n계획: {plan}\n위 지시를 수행하기 위한 진짜 결과물 텍스트를 작성해. 거짓말 금지."
            exec_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": execution_prompt}], model=self.model_groq, temperature=0.2
            )
            result_text = exec_completion.choices[0].message.content
            tool_results = self.execute_tools(plan, result_text, st.secrets)
            return "task", plan, f"{result_text}\n\n---\n**[🛠️ 무기 실제 실행 로그]**\n{tool_results}"
            
        else:
            return "chat", response.replace("[CHAT]", "").strip(), None
