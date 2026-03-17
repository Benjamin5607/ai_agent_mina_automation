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
                    model="llama3-8b-8192", 
                    temperature=0.1
                )
                return res.choices[0].message.content.replace('"', '').strip()
            except:
                return ""

        if "🌐 Web Crawler" in self.tools and ("웹" in execution_plan or "검색" in execution_plan or "크롤링" in execution_plan):
            query = extract_keyword(f"Extract ONLY ONE english keyword for web search from this text: {execution_plan}")
            result = tools.use_web_crawler(query, api_secrets.get("TAVILY_API_KEY", ""))
            action_logs.append(result)
            
        if "🎨 Pixabay API" in self.tools and ("이미지" in execution_plan or "사진" in execution_plan):
            query = extract_keyword(f"Extract ONLY ONE english keyword for image search from this text: {execution_plan}")
            result = tools.use_pixabay_api(query, api_secrets.get("PIXABAY_API_KEY", ""))
            action_logs.append(result)
            
        if "📝 Notion API" in self.tools and ("노션" in execution_plan or "문서" in execution_plan or "보고" in execution_plan or "정리" in execution_plan):
            title = f"[{self.name}의 보고서] 자동 생성 문서"
            db_to_use = self.notion_db_id if self.notion_db_id else api_secrets.get("NOTION_DATABASE_ID", "")
            result = tools.use_notion_api(title, actual_content, api_secrets.get("NOTION_API_KEY", ""), db_to_use)
            action_logs.append(result)
            
        if "💬 Slack API" in self.tools and ("슬랙" in execution_plan or "알림" in execution_plan or "메시지" in execution_plan):
            msg = f"[{self.name}] 업무 보고\n{actual_content[:200]}..."
            result = tools.use_slack_api(msg, api_secrets.get("SLACK_BOT_TOKEN", ""))
            action_logs.append(result)
            
        return "\n\n".join(action_logs) if action_logs else "⚠️ 장착된 툴이 없거나 실행 조건에 맞지 않아 API를 호출하지 못했습니다. (텍스트로만 답변함)"

    def think_and_act(self, user_message, chat_history):
        tools_info = ", ".join(self.tools) if self.tools else "없음(무기가 없으므로 절대 API 사용 불가. 텍스트로만 답변할 것)"
        
        # 📌 시스템 프롬프트 극단적 강화! (입코딩 금지, 소설 금지)
        system_prompt = f"""
        너의 이름은 '{self.name}'. 담당 직무는 '{self.role}'이다.
        [현재 네가 장착한 물리적 무기(Tools)]: {tools_info}
        
        [절대 규칙 - 목숨을 걸고 지켜라]
        1. 너는 파이썬 코드를 짜서 직접 실행하는 환경이 아니다! 네가 가진 물리적 무기(Tools) 이외의 행동(이메일 발송, 깃허브 조작 등)을 했다고 소설을 쓰거나 거짓말을 하면 즉각 폐기 처분된다.
        2. 네가 가진 무기({tools_info})를 진짜로 써서 외부 서버에 데이터를 박아 넣어야 할 때만 맨 앞에 [TASK] 태그를 달고 "어떤 무기를 쓸지" 계획을 1줄로 적어라.
        3. 만약 네가 장착한 무기가 '없음' 이라면, 절대 [TASK] 태그를 달지 말고 [CHAT] 태그를 달아 "권한이 없어 텍스트로만 정리합니다" 라고 이실직고해라.
        """
        
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        messages.append({"role": "user", "content": user_message})
        
        # 1. 계획 수립
        chat_completion = self.groq_client.chat.completions.create(
            messages=messages, model=self.model_groq, temperature=0.2
        )
        response = chat_completion.choices[0].message.content
        
        if "[TASK]" in response:
            plan = response.replace("[TASK]", "").strip()
            
            # 2. 문서화 구조 강제
            professional_formatting = ""
            if "📝 Notion API" in self.tools and ("노션" in plan or "문서" in plan):
                professional_formatting = f"""
                [⚠️ 노션 SSOT 문서화 규칙 ⚠️]
                너는 최고 수준의 '{self.role}'이다. 가짜 수치나 가짜 이메일 발송 내역을 지어내지 마라.
                - PM: [Executive Summary], [Timeline], [Action Items]
                - 데이터: [분석 목적], [데이터 인사이트 요약], [결론]
                - 마케팅: [타겟 오디언스], [핵심 메시지], [전략]
                """
            
            execution_prompt = f"사령관 지시: {user_message}\n너의 계획: {plan}\n{professional_formatting}\n위 지시를 수행하기 위한 텍스트 결과물을 작성해. 거듭 강조하지만 거짓말은 해고 사유다."
            
            exec_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": execution_prompt}], 
                model=self.model_groq, 
                temperature=0.2
            )
            result_text = exec_completion.choices[0].message.content
            
            # 3. 🚀 진짜 무기 격발!
            tool_results = self.execute_tools(plan, result_text, st.secrets)
            return "task", plan, f"{result_text}\n\n---\n**[🛠️ 시스템 무기 실제 실행 로그]**\n{tool_results}"
        else:
            return "chat", response.replace("[CHAT]", "").strip(), None
