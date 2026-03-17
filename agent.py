from groq import Groq
import streamlit as st
import tools

class LobsterAgent:
    # 📌 제미나이 키 적출! 이제 에이전트는 Groq 키만 받습니다.
    def __init__(self, groq_key, name="랍스타-01", role="만능 비서"):
        self.name = name
        self.role = role
        self.groq_client = Groq(api_key=groq_key)
        self.tools = []
        self.notion_db_id = None
        self.model_groq = "llama3-8b-8192" # 기본 뇌

    def execute_tools(self, execution_plan, actual_content, api_secrets):
        action_logs = []
        
        # 📌 툴 키워드 추출도 제미나이 대신 가볍고 빠른 Groq(Llama3-8b) 모델이 담당합니다!
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

        if "🌐 Web Crawler" in self.tools and ("웹 검색" in execution_plan or "크롤링" in execution_plan or "검색" in execution_plan):
            query = extract_keyword(f"Extract ONLY ONE english keyword for web search from this text. No other words: {execution_plan}")
            result = tools.use_web_crawler(query, api_secrets.get("TAVILY_API_KEY", ""))
            action_logs.append(result)
            
        if "🎨 Pixabay API" in self.tools and ("이미지" in execution_plan or "사진" in execution_plan):
            query = extract_keyword(f"Extract ONLY ONE english keyword for image search from this text. No other words: {execution_plan}")
            result = tools.use_pixabay_api(query, api_secrets.get("PIXABAY_API_KEY", ""))
            action_logs.append(result)
            
        if "📝 Notion API" in self.tools and ("노션" in execution_plan or "문서" in execution_plan or "보고서" in execution_plan):
            title = f"[{self.name}의 보고서] 자동 생성 문서"
            db_to_use = self.notion_db_id if self.notion_db_id else api_secrets.get("NOTION_DATABASE_ID", "")
            result = tools.use_notion_api(title, actual_content, api_secrets.get("NOTION_API_KEY", ""), db_to_use)
            action_logs.append(result)
            
        if "💬 Slack API" in self.tools and ("슬랙" in execution_plan or "알림" in execution_plan or "메시지" in execution_plan):
            msg = f"[{self.name}] 업무 보고\n{actual_content[:200]}..."
            result = tools.use_slack_api(msg, api_secrets.get("SLACK_BOT_TOKEN", ""))
            action_logs.append(result)
            
        return "\n\n".join(action_logs) if action_logs else "⚠️ 툴 작동 조건에 맞지 않아 API를 호출하지 않았습니다."

    def think_and_act(self, user_message, chat_history):
        # 📌 제미나이 모델 파라미터 삭제. 오직 자신에게 이식된 Groq 뇌만 씁니다.
        tools_info = ", ".join(self.tools) if self.tools else "없음"
        system_prompt = f"""
        너의 이름은 '{self.name}'. 담당 직무는 '{self.role}'이다.
        [장착 무기(Tools)]: {tools_info}
        1. 단순 대화면 [CHAT] 태그를 달아라.
        2. 실제 결과물을 만들고 툴을 써야 한다면 [TASK] 태그를 달고 계획을 적어라. 절대 없는 수치나 가짜 통계를 지어내지 마라.
        """
        
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        messages.append({"role": "user", "content": user_message})
        
        # 1. 계획 수립 (Groq)
        chat_completion = self.groq_client.chat.completions.create(
            messages=messages, model=self.model_groq, temperature=0.3
        )
        response = chat_completion.choices[0].message.content
        
        if "[TASK]" in response:
            plan = response.replace("[TASK]", "").strip()
            
            professional_formatting = ""
            if "📝 Notion API" in self.tools and ("노션" in plan or "문서" in plan or "보고서" in plan):
                professional_formatting = f"""
                [⚠️ 노션 SSOT 문서화 절대 규칙 ⚠️]
                너는 최고 수준의 '{self.role}'이다. 진실의 원천(SSOT) 문서를 작성해라.
                - PM/기획: [Executive Summary], [Objective], [Timeline], [RACI/담당자], [Action Items]
                - 데이터: [분석 목적], [핵심 지표(KPIs)], [데이터 인사이트 요약], [결론 및 제언]
                - 마케팅: [타겟 오디언스], [핵심 메시지], [채널 전략], [예상 ROI]
                - 기타: 헤더(#), 불릿 포인트(-), 체크리스트를 적극 활용해라.
                """
            
            execution_prompt = f"사령관 지시: {user_message}\n너의 계획: {plan}\n{professional_formatting}\n위 지시를 수행하기 위한 텍스트 결과물을 작성해. 거짓말 금지."
            
            # 2. 📌 실제 문서 작성 (제미나이 대신 이것도 Groq가 직접 처리!!)
            exec_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": execution_prompt}], 
                model=self.model_groq, 
                temperature=0.3
            )
            result_text = exec_completion.choices[0].message.content
            
            # 3. 툴 실행
            tool_results = self.execute_tools(plan, result_text, st.secrets)
            return "task", plan, f"{result_text}\n\n---\n**[🛠️ 시스템 무기 실제 실행 로그]**\n{tool_results}"
        else:
            return "chat", response.replace("[CHAT]", "").strip(), None
