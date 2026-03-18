from groq import Groq
import streamlit as st
import json
import tools
import re 

class LobsterAgent:
    def __init__(self, groq_key, name="랍스타-01", role="만능 비서"):
        self.name = name
        self.role = role
        self.groq_client = Groq(api_key=groq_key)
        self.tools = []
        self.notion_db_id = None
        self.model_groq = "llama3-8b-8192"

    def execute_tools(self, execution_plan, actual_content, api_secrets, user_message=""):
        action_logs = []
        def extract_keyword(prompt_text):
            try:
                res = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt_text}],
                    model="llama3-8b-8192", temperature=0.1
                )
                return res.choices[0].message.content.replace('"', '').strip()
            except: return ""

        if "🦆 무제한 웹검색 (무료)" in self.tools and ("검색" in execution_plan or "서치" in execution_plan):
            query = extract_keyword(f"Extract ONE english keyword for search from this: {execution_plan}")
            result = tools.use_duckduckgo_search(query)
            action_logs.append(result)

        if "🕷️ 웹페이지 읽기 (무료)" in self.tools and ("크롤링" in execution_plan or "읽기" in execution_plan or "스크랩" in execution_plan):
            urls = re.findall(r'(https?://[^\s]+)', user_message + " " + execution_plan + " " + actual_content)
            if urls:
                result = tools.use_web_scraper(urls[0])
                action_logs.append(result)

        if "💾 로컬 파일 제어 (무료)" in self.tools and ("저장" in execution_plan or "파일" in execution_plan):
            filename = extract_keyword(f"Extract a valid filename with extension (e.g. report.md, data.csv) from this: {execution_plan}")
            if not filename or "." not in filename: filename = "output_report.md"
            result = tools.use_file_system("write", filename, actual_content)
            action_logs.append(result)

        if "💻 파이썬 터미널 실행 (무료)" in self.tools and ("코드" in execution_plan or "실행" in execution_plan or "파이썬" in execution_plan):
            code_blocks = re.findall(r'```python\n(.*?)\n```', actual_content, re.DOTALL)
            code_to_run = code_blocks[0] if code_blocks else ""
            if code_to_run:
                result = tools.use_python_executor(code_to_run)
                action_logs.append(result)
            else:
                action_logs.append("⚠️ 실행할 파이썬 코드를 찾지 못했습니다.")

        if "🎬 숏폼 영상 제작기 (무료)" in self.tools and ("영상" in execution_plan or "쇼츠" in execution_plan or "릴스" in execution_plan):
            script = extract_keyword(f"Extract the Korean spoken voice script for the video from this: {actual_content}")
            prompt = extract_keyword(f"Extract a short english image prompt from this: {actual_content}. Make sure it includes 'Emily, 3D Pixar style character'.")
            result = tools.use_video_generator(script, prompt)
            action_logs.append(result)

        if "🚀 SNS 자동 업로드 (웹훅)" in self.tools and ("업로드" in execution_plan or "틱톡" in execution_plan or "인스타" in execution_plan or "유튜브" in execution_plan):
            title = extract_keyword(f"Extract the video title from this: {actual_content}")
            tags = extract_keyword(f"Extract the hashtags from this: {actual_content}")
            webhook_url = api_secrets.get("MAKE_WEBHOOK_URL", "")
            result = tools.use_sns_webhook(title, tags, webhook_url)
            action_logs.append(result)

        if "📝 Notion API" in self.tools and ("노션" in execution_plan or "문서" in execution_plan):
            title = f"[{self.name}] 보고서"
            db_to_use = self.notion_db_id if self.notion_db_id else api_secrets.get("NOTION_DATABASE_ID", "")
            result = tools.use_notion_api(title, actual_content, api_secrets.get("NOTION_API_KEY", ""), db_to_use)
            action_logs.append(result)
            
        if "💬 Slack API" in self.tools and ("슬랙" in execution_plan or "알림" in execution_plan):
            result = tools.use_slack_api(f"[{self.name}] {actual_content[:200]}...", api_secrets.get("SLACK_BOT_TOKEN", ""))
            action_logs.append(result)
            
        return "\n\n".join(action_logs) if action_logs else "⚠️ 툴 조건에 맞지 않아 실행하지 않았습니다."

    def think_and_act(self, user_message, chat_history):
        tool_desc = {
            "🦆 무제한 웹검색 (무료)": "인터넷 검색을 통해 웹 정보를 찾아옵니다.",
            "🕷️ 웹페이지 읽기 (무료)": "특정 URL의 본문 텍스트를 긁어옵니다.",
            "💾 로컬 파일 제어 (무료)": "결과물을 파일로 저장합니다.",
            "💻 파이썬 터미널 실행 (무료)": "파이썬 코드를 실행합니다.",
            "🎬 숏폼 영상 제작기 (무료)": "대본과 프롬프트만 입력하면 AI 음성(TTS)과 3D 픽사 스타일 이미지를 자동으로 생성하여 하나의 mp4 영상으로 렌더링하는 만능 툴입니다. 3D 그래픽 툴이 절대 필요 없습니다.",
            "🚀 SNS 자동 업로드 (웹훅)": "완성된 영상을 업로드합니다.",
            "📝 Notion API": "노션에 보고서를 작성합니다.",
            "💬 Slack API": "슬랙으로 알림 메시지를 전송합니다."
        }
        
        if not self.tools:
            manual = "없음 (물리적 작업 절대 불가)"
        else:
            manual = "\n".join([f"- {t}: {tool_desc.get(t, '')}" for t in self.tools])
        
        # 1차 JSON 검증
        eval_prompt = f"""
        너는 '{self.name}' (직무: {self.role})이다.
        네가 가진 무기와 그 기능은 다음과 같다:
        {manual}

        지시: "{user_message}"
        
        네가 가진 무기와 지식만으로 이 지시를 '실제로 거짓 없이' 완벽하게 수행할 수 있는가?
        (주의: 텍스트 요약, 번역, 분석, 대본 작성 등 언어적인 작업은 네 자체 지능(LLM)으로 수행 가능하므로 별도의 툴이 필요하지 않다. 물리적인 데이터 수집이나 외부 전송이 필요한 경우에만 툴 유무를 따져라.)
        
        아래 JSON 형식으로만 대답해라.
        {{
            "can_execute": true 또는 false,
            "reason": "객관적인 이유",
            "needed_resources": "false일 경우 사령관에게 요청할 사항 (true면 빈 문자열)"
        }}
        """
        try:
            eval_res = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": eval_prompt}],
                model=self.model_groq, temperature=0.0, response_format={"type": "json_object"} 
            )
            evaluation = json.loads(eval_res.choices[0].message.content)
            if not evaluation.get("can_execute"):
                reason = evaluation.get("reason", "권한 부족")
                needs = evaluation.get("needed_resources", "추가 정보/툴 연동 필요")
                return "help", f"사령관님, 지원이 필요합니다.\n- 이유: {reason}\n- 필요 사항: {needs}", None
        except: pass

        system_prompt = f"""
        너는 '{self.name}'이다. 네 무기 메뉴얼은 다음과 같다:
        {manual}
        무기를 쓸 때는 맨 앞에 [TASK] 태그를 달고 계획을 1줄로 적어라.
        """
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        messages.append({"role": "user", "content": user_message})
        
        chat_completion = self.groq_client.chat.completions.create(
            messages=messages, model=self.model_groq, temperature=0.1
        )
        response = chat_completion.choices[0].message.content

        # 📌 억울한 URL 차단 코드 삭제 완료!

        if "[NEED_HELP]" in response or "할 수 없" in response or "권한이 없" in response:
            return "help", response.replace("[NEED_HELP]", "").strip(), None
            
        elif "[TASK]" in response:
            plan = response.replace("[TASK]", "").strip()
            
            execution_prompt = f"지시: {user_message}\n계획: {plan}\n결과물 텍스트를 작성해라."
            exec_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": execution_prompt}], model=self.model_groq, temperature=0.1
            )
            result_text = exec_completion.choices[0].message.content
            
            # 📌 여기도 URL 차단 코드 삭제 완료!

            tool_results = self.execute_tools(plan, result_text, st.secrets, user_message)
            return "task", plan, f"{result_text}\n\n---\n**[🛠️ 무기 실제 실행 로그]**\n{tool_results}"
            
        else:
            return "chat", response.replace("[CHAT]", "").strip(), None
