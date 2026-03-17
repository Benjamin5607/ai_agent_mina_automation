from groq import Groq
import streamlit as st
import json
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

        if "🌐 Web Crawler" in self.tools and ("웹" in execution_plan or "크롤링" in execution_plan or "검색" in execution_plan):
            query = extract_keyword(f"Extract ONE english keyword for search: {execution_plan}")
            result = tools.use_web_crawler(query, api_secrets.get("TAVILY_API_KEY", ""))
            action_logs.append(result)
        if "🎨 Pixabay API" in self.tools and ("이미지" in execution_plan or "사진" in execution_plan):
            query = extract_keyword(f"Extract ONE english keyword for image: {execution_plan}")
            result = tools.use_pixabay_api(query, api_secrets.get("PIXABAY_API_KEY", ""))
            action_logs.append(result)
        if "📝 Notion API" in self.tools and ("노션" in execution_plan or "문서" in execution_plan or "보고" in execution_plan):
            title = f"[{self.name}] 자동 생성 문서"
            db_to_use = self.notion_db_id if self.notion_db_id else api_secrets.get("NOTION_DATABASE_ID", "")
            result = tools.use_notion_api(title, actual_content, api_secrets.get("NOTION_API_KEY", ""), db_to_use)
            action_logs.append(result)
        if "💬 Slack API" in self.tools and ("슬랙" in execution_plan or "알림" in execution_plan):
            result = tools.use_slack_api(f"[{self.name}] {actual_content[:200]}...", api_secrets.get("SLACK_BOT_TOKEN", ""))
            action_logs.append(result)
            
        return "\n\n".join(action_logs) if action_logs else "⚠️ 무기가 없거나 조건에 맞지 않아 API를 호출하지 못했습니다."

    def think_and_act(self, user_message, chat_history):
        tools_list = ", ".join(self.tools) if self.tools else "없음(물리적 작업 절대 불가)"
        
        # 📌 [핵심 1단계] 1차 검증: JSON 포맷으로 철저하게 자기 객관화!
        eval_prompt = f"""
        너는 '{self.name}' (직무: {self.role})이다.
        네가 현재 물리적으로 연결된 API 무기는 오직 [{tools_list}] 뿐이다.

        사령관의 지시: "{user_message}"

        [객관적 판단 기준]
        1. 네가 가진 무기({tools_list})만으로 이 지시를 '실제로' 완벽하게 수행할 수 있는가?
        2. 구글 애널리틱스 연동, 지라(Jira) 티켓 생성, 이메일 발송, 파일 저장 등 네 무기 목록에 없는 권한이 필요한가?
        3. 만약 툴이나 권한이 부족하다면 무조건 할 수 없다고 판단해라.

        반드시 아래 JSON 형식으로만 대답해라. (Markdown 코드 블록 없이 순수 JSON만 뱉을 것)
        {{
            "can_execute": true 또는 false,
            "reason": "왜 할 수 있는지, 혹은 왜 못 하는지 객관적인 이유",
            "needed_resources": "만약 false라면, 사령관에게 무엇을 요청해야 하는지 명확히 적어라. true면 빈 문자열"
        }}
        """
        
        try:
            # Groq의 JSON 모드를 강제하여 무조건 JSON으로만 답하게 만듭니다.
            eval_res = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": eval_prompt}],
                model=self.model_groq,
                temperature=0.0,
                response_format={"type": "json_object"} 
            )
            evaluation = json.loads(eval_res.choices[0].message.content)
            
            # 자격 미달 시 즉시 SOS! (입코딩 원천 봉쇄)
            if not evaluation.get("can_execute"):
                reason = evaluation.get("reason", "물리적 권한 및 무기 부족")
                needs = evaluation.get("needed_resources", "사령관님의 추가 정보/툴 연동")
                return "help", f"사령관님, 지원이 필요합니다.\n- 이유: {reason}\n- 필요 사항: {needs}", None

        except Exception as e:
            print(f"JSON 파싱 실패 (안전장치 발동): {e}")
            pass # 파싱에 실패하면 일단 2단계로 넘겨서 처리

        # 📌 [핵심 2단계] 위 검증을 통과한 '진짜 할 수 있는 일'만 실행!
        system_prompt = f"""
        너는 '{self.name}'이다. 네 무기는 [{tools_list}] 이다.
        너는 1차 검증을 통과했다. 이제 사령관의 지시를 수행해라.
        무기를 쓸 때는 맨 앞에 [TASK] 태그를 달고 "어떤 무기를 쓸지" 1줄로 계획을 적어라.
        """
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        messages.append({"role": "user", "content": user_message})
        
        chat_completion = self.groq_client.chat.completions.create(
            messages=messages, model=self.model_groq, temperature=0.1
        )
        response = chat_completion.choices[0].message.content

        if "[TASK]" in response:
            plan = response.replace("[TASK]", "").strip()
            
            execution_prompt = f"지시: {user_message}\n계획: {plan}\n결과물 텍스트를 작성해라. (실제 존재하는 데이터만 적을 것)"
            exec_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": execution_prompt}], model=self.model_groq, temperature=0.1
            )
            result_text = exec_completion.choices[0].message.content
            
            tool_results = self.execute_tools(plan, result_text, st.secrets)
            return "task", plan, f"{result_text}\n\n---\n**[🛠️ 무기 실제 실행 로그]**\n{tool_results}"
            
        else:
            return "chat", response.replace("[CHAT]", "").strip(), None
