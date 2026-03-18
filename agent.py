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

        if "🎬 숏폼 영상 제작기 (무료)" in self.tools and ("영상" in execution_plan or "쇼츠" in execution_plan):
            # 1. AI 렌더링에 쓸 영문 이미지 프롬프트 추출 (기존 로직 유지)
            prompt = extract_keyword(f"Extract a short english image prompt from this: {actual_content}. Make sure it includes 'Emily, 3D Pixar style character'.")

            # 2. 🌟 [신규] LLM을 사용하여 상황 묘사(actual_content) 기반 전문 쇼츠 대본 자동 생성!
            st.caption("✍️ 랍스타 군단이 전문 쇼츠 대본을 작성하는 중입니다...")
            
            # 전문 쇼츠 작가 프롬프트
            script_writer_prompt = f"""
            너는 100만 유튜버의 전문 쇼츠 대본 작가다.
            아래 [상황 묘사]를 바탕으로 시청자를 끄는 매력적인 한국어 음성 합성(TTS) 대본을 작성해라.
            - 길이: 30초 내외 (2~3문장)
            - 톤앤매너: 발랄하고, 친근하고, 흥미진진하게 (에밀리 캐릭터에 맞게)
            - [주의] 오직 성우가 읽을 '말하기(Spoken)' 텍스트만 출력해라. 상황 묘사나 지시문은 절대 섞지 마라.
            - 결과물 언어: 한국어
            
            [사령관 지시]: {execution_plan}
            [상황 묘사]: {actual_content}
            전문 대본:
            """
            try:
                # 대본 작가 전용 LLM 사격! (8B 모델도 이 정도는 잘합니다 ㅋㅋ)
                script_completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": script_writer_prompt}],
                    model="llama3-8b-8192", temperature=0.7 # 약간의 창의력 주입
                )
                generated_script = script_completion.choices[0].message.content.strip()
            except:
                # LLM 작성이 실패했을 때만 최후의 fallback 사용
                generated_script = f"안녕하세요! 에밀리의 {execution_plan} 영상입니다. 함께 감상해 보시죠!"

            # 3. 렌더링 로그에 자동 생성된 대본 표시 (CCTV용)
            action_logs.append(f"✍️ [쇼츠 작가 자동 대본 생성]: {generated_script}")
            
            # 4. 이제 완벽한 대본과 프롬프트를 들고 진짜 툴을 격발!
            result = tools.use_video_generator(generated_script, prompt)
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
        # 📌 agent.py 내부: 핑계 원천 차단용 상세 무기 메뉴얼!
        tool_desc = {
            "🦆 무제한 웹검색 (무료)": (
                "인터넷 검색 엔진(DuckDuckGo)입니다. 최신 정보, 뉴스, 맛집 추천, 트렌드 등을 찾을 때 무조건 이 툴을 사용하세요. "
                "별도의 맛집 전용 API나 유료 데이터베이스(DB)가 없어도 이 툴만으로 모든 검색이 가능합니다. 핑계 대지 마세요."
            ),
            "🕷️ 웹페이지 읽기 (무료)": (
                "특정 웹사이트 URL에 접속하여 본문 텍스트를 긁어옵니다. "
                "[주의] 긁어온 외국어 텍스트를 한국어로 번역하거나, 긴 글을 3줄로 요약하는 작업은 네 자체 지능(LLM)으로 충분히 가능합니다. "
                "절대 사령관에게 번역 API나 자연어 처리 툴을 요구하지 말고 네 머리로 직접 요약/번역하세요."
            ),
            "💾 로컬 파일 제어 (무료)": (
                "사령관의 지시 결과물을 마크다운(.md), 텍스트(.txt), 파이썬(.py) 등의 파일로 서버의 가상 하드디스크에 저장합니다. "
                "외부 클라우드 가입이나 깃허브 연동 권한이 없어도 단독으로 완벽하게 작동합니다."
            ),
            "💻 파이썬 터미널 실행 (무료)": (
                "복잡한 수학 계산, 데이터 정제, 알고리즘 실행이 필요할 때 네가 작성한 파이썬 코드를 실제 서버에서 대신 실행해 줍니다. "
                "계산기 툴이 없다고 징징대지 말고 이 툴로 코드를 짜서 계산하세요."
            ),
            "🎬 숏폼 영상 제작기 (무료)": (
                "[가장 중요] 대본(한국어/영어)과 화면 프롬프트(영어)만 입력하면, 이 툴이 알아서 AI 음성 합성(TTS)과 "
                "AI 이미지 생성(3D 픽사 애니메이션, 수채화, 실사 등 모든 화풍)을 100% 수행한 뒤 mp4 영상으로 렌더링합니다. "
                "3D 모델링 툴(Maya, Blender), 애니메이션 소프트웨어, 외부 성우 연동이 **절대** 필요 없습니다. 이 툴 하나로 끝납니다."
            ),
            "🚀 SNS 자동 업로드 (웹훅)": (
                "완성된 영상이나 텍스트를 틱톡, 인스타그램, 유튜브 등에 자동으로 전송합니다. "
                "복잡한 소셜 미디어 로그인(OAuth) 계정 정보나 연동 권한을 사령관에게 요구하지 마세요. "
                "이미 백그라운드 웹훅으로 세팅되어 있으니 너는 그냥 데이터만 쏘면 됩니다."
            ),
            "📝 Notion API": (
                "최종 정리된 텍스트 보고서를 사령관의 노션 데이터베이스에 깔끔하게 업로드합니다. (API 키 필요)"
            ),
            "💬 Slack API": (
                "작업 완료 상태나 중요 알림을 사령관의 슬랙 메신저로 즉시 전송합니다. (API 키 필요)"
            )
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
