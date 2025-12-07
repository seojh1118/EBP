import streamlit as st
import speech_recognition as sr
import time
import random 
import requests
import datetime
import os
import re
import json 
import pandas as pd
import numpy as np
import joblib
import base64
from pytrends.request import TrendReq
from gtts import gTTS
import pygame
import plotly.express as px
import plotly.graph_objects as go 

# [NEW] Upstage API 사용을 위한 OpenAI 클라이언트
from openai import OpenAI

# --- 0. 설정 및 데이터베이스 ---
STATE_FILE = "state.json"
GUIDE_FILE = "guide_voice.mp3" 

# 👉 여기에 Upstage API 키를 입력하세요! (예: "up_sk_...")
UPSTAGE_API_KEY = "up_PNXUPbQH9s3ATByYfA4m90NpL0DQe" 

# [안전장치] 영생 단어 목록
IMMORTAL_WORDS = [
    "엄마", "아빠", "사랑", "가족", "친구", "학교", "선생님", "밥", "물", "집", 
    "나", "너", "우리", "대한민국", "한국", "서울", "행복", "사람", "하늘", "바다",
    "안녕하세요", "감사합니다", "안녕", "돈", "회사", "꿈", "커피", "치킨"
]

# [전시용] 유명 신조어 DB
KNOWN_SLANGS = {
    "꿀잼": {"months": 36, "reason": "'노잼', '핵노잼' 등 파생어를 낳으며 스테디셀러로 등극"},
    "노잼": {"months": 36, "reason": "재미없다는 말을 대체할 단어가 없어 장수 중"},
    "존맛": {"months": 24, "reason": "비속어 어원이 희석되어 맛집 필수 용어가 됨"},
    "즐": {"months": 60, "reason": "2000년대 초반을 지배한 전설적인 단어"},
    "안습": {"months": 36, "reason": "지상렬이 만든 불후의 명작"},
    "뭥미": {"months": 18, "reason": "오타에서 시작된 유행어"},
    "지못미": {"months": 24, "reason": "지켜주지 못해 미안해의 줄임말"},
    "킹왕짱": {"months": 12, "reason": "강조 표현의 시초격"},
    "우왕ㅋ굳ㅋ": {"months": 6, "reason": "2000년대 후반 웹툰에서 유래한 반짝 유행어"},
    "쩔어": {"months": 120, "reason": "감탄사로 완전히 정착하여 생명력이 깁니다"},
    "레알": {"months": 100, "reason": "Real의 발음, 거의 표준어급 생존력"},
    "에바": {"months": 80, "reason": "오버하다의 변형, 학생들 사이에서 꾸준함"},
    "깜놀": {"months": 48, "reason": "깜짝 놀라다의 줄임말, 대체어가 없음"},
    "멘붕": {"months": 90, "reason": "멘탈 붕괴, 뉴스에서도 쓰는 단어"},
    "볼매": {"months": 30, "reason": "볼수록 매력있다, 긍정적 칭찬"},
    "금사빠": {"months": 50, "reason": "연애 유형을 설명하는 필수 단어"},
    "썸": {"months": 130, "reason": "사랑보다 먼 우정보다 가까운, 대체 불가"},
    "심쿵": {"months": 70, "reason": "설렘을 표현하는 가장 완벽한 두 글자"},
    "뇌섹남": {"months": 24, "reason": "방송 트렌드와 함께 흥했다가 식음"},
    "사이다": {"months": 85, "reason": "답답함을 해소하는 상황을 뜻하는 관용어"},
    "고답이": {"months": 12, "reason": "고구마 답답이, 사이다의 반대말"},
    "세젤예": {"months": 18, "reason": "세상에서 제일 예쁜, 아이돌 팬덤 용어"},
    "낄끼빠빠": {"months": 15, "reason": "사회생활의 진리를 담은 명언"},
    "비담": {"months": 12, "reason": "비주얼 담당, 아이돌 용어"},
    "팩폭": {"months": 65, "reason": "팩트 폭력, 뼈 때리는 말"},
    "TMI": {"months": 70, "reason": "정보 과잉 시대를 반영한 용어"},
    "갑분싸": {"months": 40, "reason": "분위기 파악 못하는 상황에 제격"},
    "소확행": {"months": 60, "reason": "무라카미 하루키 소설에서 유래한 라이프스타일"},
    "인싸": {"months": 80, "reason": "아웃사이더의 반대말, 사회적 계급 용어"},
    "아싸": {"months": 90, "reason": "자조적인 뉘앙스로 계속 살아남음"},
    "워라밸": {"months": 100, "reason": "직장인들의 영원한 소망"},
    "JMT": {"months": 18, "reason": "정말 맛있다를 강조, 존맛탱"},
    "얼죽아": {"months": 55, "reason": "한국인의 커피 취향을 대변함"},
    "만렙": {"months": 150, "reason": "게임 용어가 일상으로 완벽히 정착"},
    "득템": {"months": 140, "reason": "쇼핑 용어로 굳어짐"},
    "품절남": {"months": 12, "reason": "결혼한 남자를 뜻하는 말"},
    "엄친아": {"months": 100, "reason": "비교 문화가 낳은 최고의 단어"},
    "베이글녀": {"months": 10, "reason": "외모 지상주의 용어, 지금은 잘 안 씀"},
    "차도남": {"months": 12, "reason": "드라마 시크릿가든 시절 유행어"},
    "꼬꼬무": {"months": 24, "reason": "방송 프로그램 제목 줄임말"},
    "머선129": {"months": 6, "reason": "강호동 사투리 밈, 반짝 유행"},
    "킹받네": {"months": 30, "reason": "침착맨 유행어, 열받네를 대체함"},
    "억까": {"months": 36, "reason": "억지로 까다, 인터넷 방송 필수 용어"},
    "갓생": {"months": 48, "reason": "MZ세대의 부지런한 삶을 표현"},
    "캘박": {"months": 20, "reason": "캘린더 박제, 일정 잡을 때 씀"},
    "드가자": {"months": 4, "reason": "주식/코인 투자자들의 구호"},
    "폼미쳤다": {"months": 8, "reason": "칭찬 밈, 유행 주기가 짧음"},
    "중꺾마": {"months": 24, "reason": "중요한 건 꺾이지 않는 마음"},
    "너T야": {"months": 3, "reason": "MBTI 과몰입 밈, 피로도 높음"},
    "농협은행": {"months": 2, "reason": "너무 예쁘네요 -> 농협은행, 숏폼 밈"},
    "잼민이": {"months": 60, "reason": "초등학생을 지칭하는 대표 단어"},
    "알잘딱깔센": {"months": 24, "reason": "알아서 잘 딱 깔끔하게 센스있게"},
    "오운완": {"months": 40, "reason": "운동 인증샷 필수 해시태그"},
    "스불재": {"months": 18, "reason": "스스로 불러온 재앙"},
    "가즈아": {"months": 6, "reason": "투기 열풍의 상징"},
    "분조장": {"months": 50, "reason": "분노 조절 장애, 화많은 현대인"},
    "알파세대": {"months": 48, "reason": "Z세대 다음 세대를 지칭"},
    "어쩔티비": {"months": 6, "reason": "저연령층의 말대꾸 유행어"},
}

# --- 1. 상태 저장 함수 ---
def update_projector(color, main_text, status="active", sub_text=""):
    state = {
        "status": status,
        "color": color,
        "text": main_text,      
        "sub_text": sub_text,   
        "timestamp": time.time()
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Projector Update Error: {e}")

# --- 2. 표준어 확인 ---
def check_is_standard_word(word):
    if word in IMMORTAL_WORDS: return True
    API_KEY = "C39F8A5DC5EEAE06C1307EDF6450E52B" 
    url = "https://stdict.korean.go.kr/api/search.do"
    params = {"key": API_KEY, "q": word, "req_type": "json", "advanced": "y", "method": "exact"}
    try:
        response = requests.get(url, params=params, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data and 'channel' in data and 'total' in data['channel']:
                if int(data['channel']['total']) > 0: return True
        return False 
    except: return False

# --- 3. [NEW] Upstage LLM 분석 함수 ---
def analyze_with_upstage(word):
    """
    Upstage Solar API를 사용하여 단어를 분석합니다.
    """
    if not UPSTAGE_API_KEY:
        return None # 키가 없으면 시뮬레이션으로 전환

    try:
        client = OpenAI(
            api_key=UPSTAGE_API_KEY,
            base_url="https://api.upstage.ai/v1/solar"
        )
        
        prompt = f"""
        단어: "{word}"
        역할: 한국어 신조어 및 밈 분석 전문가.
        작업: 위 단어의 성격을 분석하여 JSON으로 응답.
        
        [필수 응답 형식]
        {{
            "is_offensive": false,  // 비속어/혐오표현 여부
            "months": 24,           // 예상 수명 (0~60개월, 비속어면 0)
            "reason": "..."         // 이유 (한국어 한 문장으로 간결하고 재치있게)
        }}
        """

        response = client.chat.completions.create(
            model="solar-1-mini-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        # JSON 파싱 (코드 블록 제거 등 정제)
        content = re.sub(r'```json\s*|\s*```', '', content).strip()
        result = json.loads(content)
        return result

    except Exception as e:
        print(f"Upstage API Error: {e}")
        return None # 에러 발생 시 시뮬레이션으로 전환

# --- 4. 시뮬레이션 데이터 생성 (그래프용 & 백업용) ---
def generate_simulation_data(word, override_months=None):
    random.seed(hash(word))
    np.random.seed(abs(hash(word)) % (2**32))
    dates = pd.date_range(end=datetime.date.today(), periods=52, freq='W')
    
    base = np.random.randint(0, 5, size=52)
    peak_loc = np.random.randint(10, 40)
    rise_speed = np.random.randint(2, 8)
    decay_speed = np.random.randint(2, 8)
    
    # LLM이 예측한 수명에 따라 그래프 기울기 조정
    if override_months is not None:
        if override_months < 6: decay_speed = 10 
        elif override_months > 36: decay_speed = 1

    trend = np.zeros(52)
    for i in range(peak_loc): trend[i] = (i / peak_loc) ** rise_speed * 100
    for i in range(peak_loc, 52): trend[i] = 100 * np.exp(-0.1 * decay_speed * (i - peak_loc))
        
    final_values = np.clip(trend + base + np.random.normal(0, 3, 52), 0, 100)
    series = pd.Series(final_values, index=dates, name=word)
    return series

# --- 5. 안내 음성 ---
def play_guide_voice():
    if not os.path.exists(GUIDE_FILE):
        try:
            tts = gTTS(text="신조어를 말씀해주세요.", lang='ko')
            tts.save(GUIDE_FILE)
        except: return
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(GUIDE_FILE)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except: pass

# --- 6. 음성 인식 ---
def on_stt_button_click():
    r = sr.Recognizer()
    try:
        play_guide_voice()
        with sr.Microphone() as source:
            st.toast("👂 듣고 있습니다...", icon="🎙️")
            update_projector("#FFFF00", "청취 중...", "listening") 
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
            st.session_state.text = r.recognize_google(audio, language='ko-KR')
    except sr.WaitTimeoutError:
        st.warning("⚠️ 입력 시간이 초과되었습니다.")
        update_projector("#000000", "", "standby")
    except Exception as e:
        st.error(f"오류: {e}")
        update_projector("#000000", "", "standby")

# --- 7. 스타일 ---
def load_css():
    if os.path.exists("style.css"):
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# --- 8. 메인 앱 ---
def main():
    st.set_page_config(page_title="단어 멸망 시계", layout="centered") 
    load_css()
    
    st.markdown("""
    <style>
    .clock-container {
        position: fixed; top: 30px; left: 30px; z-index: 9999; 
        pointer-events: none; font-family: 'Courier New', monospace;
        display: flex; flex-direction: column; gap: 15px;
    }
    .digital-clock {
        background: rgba(0, 0, 0, 0.7); border: 1px solid rgba(0, 255, 255, 0.3);
        padding: 10px 15px; border-radius: 5px; width: 220px;
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.1); backdrop-filter: blur(5px);
    }
    .label { font-size: 0.8rem; color: #00FFFF; margin-bottom: 5px; letter-spacing: 1px; }
    .time { font-size: 1.8rem; font-weight: bold; color: #FFFFFF; text-shadow: 0 0 5px rgba(255, 255, 255, 0.8); letter-spacing: 2px; }
    #clock-random .time, #clock-random .label { color: #FF0055; text-shadow: 0 0 5px rgba(255, 0, 85, 0.8); }
    </style>

    <div class="clock-container">
        <div class="digital-clock"><div class="label">SEOUL (KST)</div><div class="time" id="time-kr">--:--:--</div></div>
        <div class="digital-clock"><div class="label">NEW YORK (EST)</div><div class="time" id="time-us">--:--:--</div></div>
        <div class="digital-clock" id="clock-random"><div class="label">UNKNOWN DATA</div><div class="time" id="time-rand">000000</div></div>
    </div>

    <script>
    (function() {
        if (window.clockInterval) clearInterval(window.clockInterval);
        function updateClocks() {
            const now = new Date();
            const krElement = document.getElementById('time-kr');
            const usElement = document.getElementById('time-us');
            const randElement = document.getElementById('time-rand');
            if (!krElement || !usElement || !randElement) return; 
            krElement.innerText = now.toLocaleTimeString('en-US', {timeZone: 'Asia/Seoul', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'});
            usElement.innerText = now.toLocaleTimeString('en-US', {timeZone: 'America/New_York', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'});
            randElement.innerText = Math.floor(Math.random() * 900000) + 100000;
        }
        const checkExist = setInterval(function() {
           if (document.getElementById('time-kr')) {
              clearInterval(checkExist);
              window.clockInterval = setInterval(updateClocks, 100);
              updateClocks();
           }
        }, 100);
    })();
    </script>
    """, unsafe_allow_html=True)
    
    if not os.path.exists(STATE_FILE):
        update_projector("#000000", "", "standby")

    if os.path.exists("img/smoke.mp4"):
        try:
            v_b64 = base64.b64encode(open("img/smoke.mp4", "rb").read()).decode()
            st.markdown(f'<video autoplay muted loop playsinline style="width:100%; opacity:0.6;"><source src="data:video/mp4;base64,{v_b64}"></video>', unsafe_allow_html=True)
        except: pass

    st.markdown('<h1 class="title-text"><span>☯︎단어 멸망 시계☯︎</span></h1>', unsafe_allow_html=True)
    
    input_method = st.radio("입력 방식 선택:", ["🎙️ 음성으로 입력", "⌨️ 키보드로 입력"], horizontal=True, label_visibility="collapsed")

    st.markdown("<p style='text-align: center; color: #ccc;'>신조어를 말하면 멸망까지 남은 시간을 예측합니다.</p>", unsafe_allow_html=True)
    
    if "🎙️" in input_method:
        st.button("🎙️ 음성 입력 시작", on_click=on_stt_button_click, use_container_width=True)
    else:
        with st.form("text_input_form"):
            user_text = st.text_input("분석할 단어를 입력하세요:", placeholder="예: 꿀잼, 중꺾마...")
            submitted = st.form_submit_button("🔍 분석 시작", use_container_width=True)
            if submitted and user_text:
                st.session_state.text = user_text

    if "text" in st.session_state and st.session_state.text:
        text = st.session_state.text.strip()
        st.markdown(f"<div class='user-input'>입력된 단어: \"{text}\"</div>", unsafe_allow_html=True)

        update_projector("#9900FF", "분석 중...", "analyzing")
        
        months = 0
        reason = ""
        series = None
        status_msg = ""
        color = "#000000"
        
        bad_words = ["시발", "병신", "개새", "존나", "졸라", "충", "느금", "섹스", "미친", "닥쳐", "씨발", "좆"] 
        if any(bw in text for bw in bad_words):
            st.error("🚫 비속어 감지됨")
            update_projector("#FF0000", "비속어", "result", "FILTERED")
            st.stop()

        if check_is_standard_word(text):
            st.success(f"♾️ 영생 (표준어): {text}")
            update_projector("#BC13FE", text, "result", "영생 (Immortal)")
            if st.button("초기화"): 
                update_projector("#000000", "", "standby")
                del st.session_state.text
                st.rerun()
            st.stop()

        # 분석 시작
        if text in KNOWN_SLANGS:
            info = KNOWN_SLANGS[text]
            months = info['months']
            reason = info['reason'] + " (데이터베이스 매칭)"
            series = generate_simulation_data(text, months)
        else:
            with st.spinner("AI(Upstage)가 유행 패턴을 분석 중입니다..."):
                # 1. Upstage API 시도
                llm_result = analyze_with_upstage(text)
                
                if llm_result:
                    if llm_result.get('is_offensive'):
                        st.error("🚫 비속어 감지됨 (AI 분석)")
                        update_projector("#FF0000", "비속어", "result", "FILTERED")
                        st.stop()
                    
                    months = int(llm_result.get('months', 12))
                    reason = llm_result.get('reason', 'AI 분석 결과')
                    series = generate_simulation_data(text, months)
                else:
                    # 2. 실패 시 -> 랜덤 시뮬레이션
                    random.seed(hash(text))
                    months = random.randint(3, 60)
                    reason = "일반적인 유행 패턴 (모델 없음)"
                    series = generate_simulation_data(text, months)

        if months <= 0:
            color = "#880000" 
            status_msg = "소멸 (DEAD)"
        elif months < 12:
            color = "#FF4500" 
            status_msg = f"수명: {months}개월"
        elif months < 36:
            color = "#00FF00" 
            status_msg = f"수명: {months}개월"
        else:
            color = "#0000FF" 
            status_msg = f"수명: {months}개월"

        for i in range(5, 0, -1):
            update_projector("#FFFFFF", str(i), "countdown", "") 
            time.sleep(1.0) 

        update_projector(color, text, "result", status_msg)
        
        st.success(f"✅ 예측 결과: {status_msg}")
        st.info(f"분석 이유: {reason}")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("예측 수명", status_msg)
        col2.metric("상태", "양호" if months > 12 else "위험")
        
        if series is not None:
            chart_df = series.reset_index()
            chart_df.columns = ['Date', 'Interest']
            fig = px.line(chart_df, x='Date', y='Interest')
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#E0E0E0'),
                xaxis=dict(showgrid=False, title="", showticklabels=True),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', title=""),
                margin=dict(l=0, r=0, t=20, b=20),
                hovermode="x unified"
            )
            fig.update_traces(line_color='#BC13FE', line_width=4)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        st.divider()
        if st.button("초기화 (대기모드)"):
            update_projector("#000000", "", "standby")
            del st.session_state.text
            st.rerun()

if __name__ == "__main__":
    main()
