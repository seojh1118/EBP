import streamlit as st
import speech_recognition as sr
import time
import random 
import requests
import os
import datetime
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
from openai import OpenAI

STATE_FILE = "state.json"
GUIDE_FILE = "guide_voice.mp3" 
UPSTAGE_API_KEY = "up_PNXUPbQH9s3ATByYfA4m90NpL0DQe" 
IMMORTAL_WORDS = [
    "엄마", "아빠", "사랑", "가족", "친구", "학교", "선생님", "밥", "물", "집", 
    "나", "너", "우리", "대한민국", "한국", "서울", "행복", "사람", "하늘", "바다",
    "안녕하세요", "감사합니다", "안녕", "돈", "회사", "꿈", "커피", "치킨"
]
KNOWN_SLANGS = {
    "꿀잼": 36, "노잼": 36, "존맛": 24, "즐": 60, "안습": 36, "뭥미": 18, 
    "지못미": 24, "킹왕짱": 12, "우왕ㅋ굳ㅋ": 6, "쩔어": 120, "레알": 100, 
    "에바": 80, "깜놀": 48, "멘붕": 90, "볼매": 30, "금사빠": 50, "썸": 130, 
    "심쿵": 70, "뇌섹남": 24, "사이다": 85, "고답이": 12, "세젤예": 18, 
    "낄끼빠빠": 15, "비담": 12, "팩폭": 65, "TMI": 70, "갑분싸": 40, 
    "소확행": 60, "인싸": 80, "아싸": 90, "워라밸": 100, "JMT": 18, 
    "얼죽아": 55, "만렙": 150, "득템": 140, "품절남": 12, "엄친아": 100, 
    "베이글녀": 10, "차도남": 12, "꼬꼬무": 24, "머선129": 6, "킹받네": 30, 
    "억까": 36, "갓생": 48, "캘박": 20, "드가자": 4, "폼미쳤다": 8, 
    "중꺾마": 24, "너T야": 3, "농협은행": 2, "잼민이": 60, "알잘딱깔센": 24, 
    "오운완": 40, "스불재": 18, "가즈아": 6, "분조장": 50, "알파세대": 48, 
    "어쩔티비": 6
}

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

@st.cache_resource
def load_assets():
    try:
        if not os.path.exists('knn_model.pkl'): return None, None, None, None, None, None
        knn_model = joblib.load('knn_model.pkl')
        scaler = joblib.load('scaler.pkl')
        return knn_model, scaler
    except: return None, None

def generate_simulation_data(word, override_months=None):
    random.seed(hash(word))
    np.random.seed(abs(hash(word)) % (2**32))
    dates = pd.date_range(end=datetime.date.today(), periods=52, freq='W')
    base = np.random.randint(0, 5, size=52)
    peak_loc = np.random.randint(10, 40)
    rise_speed = np.random.randint(2, 8)
    decay_speed = np.random.randint(2, 8)
    if override_months is not None:
        if override_months < 6: decay_speed = 10 
        elif override_months > 36: decay_speed = 1
    trend = np.zeros(52)
    for i in range(peak_loc): trend[i] = (i / peak_loc) ** rise_speed * 100
    for i in range(peak_loc, 52): trend[i] = 100 * np.exp(-0.1 * decay_speed * (i - peak_loc))
    final_values = np.clip(trend + base + np.random.normal(0, 3, 52), 0, 100)
    series = pd.Series(final_values, index=dates, name=word)
    slopes = series.diff().fillna(0)
    max_rise = slopes[slopes > 0].max() if not slopes[slopes > 0].empty else 0
    decay_rate = series.loc[series.idxmax():].mean() if len(series.loc[series.idxmax():]) > 1 else 0
    return [len(word), float(max_rise), float(series.std()), float(decay_rate)], series

def get_realtime_features(word):
    try:
        pytrends = TrendReq(hl='ko-KR', tz=540, timeout=(3, 5))
        today = datetime.date.today()
        one_year = today - datetime.timedelta(days=365)
        pytrends.build_payload([word], cat=0, timeframe=f'{one_year} {today}', geo='KR')
        df = pytrends.interest_over_time()
        if not df.empty and word in df.columns and df[word].sum() > 0:
            series = df[word]
            slopes = series.diff().fillna(0)
            max_rise = slopes[slopes > 0].max() if not slopes[slopes > 0].empty else 0
            decay = series.loc[series.idxmax():].mean() if len(series.loc[series.idxmax():]) > 1 else 0
            return [len(word), float(max_rise), float(series.std()), float(decay)], series, False
    except: pass
    feat, ser = generate_simulation_data(word)
    return feat, ser, True

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

def load_css():
    if os.path.exists("style.css"):
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def analyze_with_upstage(word):
    if not UPSTAGE_API_KEY:
        return None 
    try:
        client = OpenAI(
            api_key=UPSTAGE_API_KEY,
            base_url="https://api.upstage.ai/v1/solar"
        )
        prompt = f"""
        단어: "{word}"
        역할: 한국어 신조어 및 밈 전문가.
        작업: 위 단어에 대한 분석 정보를 JSON으로 응답.
        
        [필수 응답 형식]
        {{
            "is_offensive": false,  
            "months": 24,           
            "example": "..."         
        }}
        
        [가이드라인]
        - example: 이 단어를 사용한 가장 자연스럽고 재치 있는 한국어 예문 한 문장. (인터넷 댓글이나 대화체 느낌)
        - months: 예상 수명 (0~60). 비속어면 0.
        - 예시 (단어: 중꺾마): "이번 시험 망쳤지만 괜찮아, 중요한 건 꺾이지 않는 마음이니까!"
        """
        response = client.chat.completions.create(
            model="solar-1-mini-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        content = response.choices[0].message.content
        content = re.sub(r'```json\s*|\s*```', '', content).strip()
        result = json.loads(content)
        return result
    except Exception as e:
        print(f"Upstage API Error: {e}")
        return None 

def main():
    st.set_page_config(page_title="단어 멸망 시계", layout="centered") 
    load_css()
    
    st.markdown("""
<style>
.clock-container {
    position: fixed; top: 20px; left: 20px; z-index: 9999; 
    pointer-events: none; font-family: 'Courier New', monospace;
    display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
}
.right-container {
    position: fixed; top: 20px; right: 20px; z-index: 9999;
    pointer-events: none; font-family: 'Courier New', monospace;
    display: flex; flex-direction: column; gap: 15px; align-items: flex-end;
}
.digital-clock, .status-box {
    background: rgba(0, 0, 0, 0.7); border: 1px solid rgba(0, 255, 255, 0.2);
    padding: 5px 10px; border-radius: 5px; width: 160px;
    box-shadow: 0 0 5px rgba(0, 255, 255, 0.1); backdrop-filter: blur(2px);
}
.label { font-size: 0.7rem; color: #00FFFF; margin-bottom: 2px; letter-spacing: 1px; }
.time { font-size: 1.2rem; font-weight: bold; color: #FFFFFF; text-shadow: 0 0 3px rgba(255, 255, 255, 0.8); }
.random-clock .time, .random-clock .label { color: #FF0055 !important; text-shadow: 0 0 3px rgba(255, 0, 85, 0.8) !important; }
.status-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: #fff; margin-bottom: 5px; }
.dot { height: 8px; width: 8px; background-color: #00FF00; border-radius: 50%; display: inline-block; margin-right: 5px; box-shadow: 0 0 5px #00FF00; animation: blink 1s infinite; }
.bar-container { width: 80px; height: 5px; background: #333; margin-top: 2px; }
.bar-fill { height: 100%; background: #FF00FF; width: 0%; animation: loadBar 2s infinite; }
.equalizer { display: flex; gap: 3px; height: 30px; align-items: flex-end; margin-top: 5px; }
.eq-bar { width: 5px; background: #00FFFF; animation: eqAnim 0.5s infinite ease-in-out alternate; }
@keyframes blink { 50% { opacity: 0.3; } }
@keyframes loadBar { 0% { width: 10%; } 50% { width: 90%; } 100% { width: 40%; } }
@keyframes eqAnim { 0% { height: 5px; } 100% { height: 30px; } }
</style>

<div class="clock-container">
    <div class="digital-clock"><div class="label">SEOUL (KST)</div><div class="time" data-timezone="Asia/Seoul">--:--:--</div></div>
    <div class="digital-clock"><div class="label">NEW YORK (EST)</div><div class="time" data-timezone="America/New_York">--:--:--</div></div>
    <div class="digital-clock"><div class="label">LONDON (GMT)</div><div class="time" data-timezone="Europe/London">--:--:--</div></div>
    <div class="digital-clock"><div class="label">PARIS (CET)</div><div class="time" data-timezone="Europe/Paris">--:--:--</div></div>
    <div class="digital-clock"><div class="label">ROME (CET)</div><div class="time" data-timezone="Europe/Rome">--:--:--</div></div>
    <div class="digital-clock"><div class="label">BERLIN (CET)</div><div class="time" data-timezone="Europe/Berlin">--:--:--</div></div>
    <div class="digital-clock"><div class="label">SINGAPORE</div><div class="time" data-timezone="Asia/Singapore">--:--:--</div></div>
    <div class="digital-clock"><div class="label">KUALA LUMPUR</div><div class="time" data-timezone="Asia/Kuala_Lumpur">--:--:--</div></div>
    <div class="digital-clock"><div class="label">BEIJING</div><div class="time" data-timezone="Asia/Shanghai">--:--:--</div></div>
    <div class="digital-clock"><div class="label">TOKYO</div><div class="time" data-timezone="Asia/Tokyo">--:--:--</div></div>
    <div class="digital-clock"><div class="label">HANOI</div><div class="time" data-timezone="Asia/Ho_Chi_Minh">--:--:--</div></div>
    <div class="digital-clock"><div class="label">SYDNEY</div><div class="time" data-timezone="Australia/Sydney">--:--:--</div></div>
    <div class="digital-clock"><div class="label">MEXICO CITY</div><div class="time" data-timezone="America/Mexico_City">--:--:--</div></div>
    <div class="digital-clock"><div class="label">TORONTO</div><div class="time" data-timezone="America/Toronto">--:--:--</div></div>
    <div class="digital-clock random-clock"><div class="label">UNKNOWN DATA</div><div class="time" id="time-rand">000000</div></div>
</div>

<div class="right-container">
    <div class="status-box">
        <div class="label">SYSTEM STATUS</div>
        <div class="status-row"><span class="dot"></span> SERVER: ONLINE</div>
        <div class="status-row"><span class="dot"></span> API: LINKED</div>
        <div class="status-row"><span class="dot"></span> DB: CONNECTED</div>
    </div>
    <div class="status-box">
        <div class="label">AUDIO INPUT</div>
        <div class="equalizer">
            <div class="eq-bar" style="animation-delay: 0s"></div>
            <div class="eq-bar" style="animation-delay: 0.1s"></div>
            <div class="eq-bar" style="animation-delay: 0.2s"></div>
            <div class="eq-bar" style="animation-delay: 0.3s"></div>
            <div class="eq-bar" style="animation-delay: 0.4s"></div>
            <div class="eq-bar" style="animation-delay: 0.5s"></div>
            <div class="eq-bar" style="animation-delay: 0.2s"></div>
            <div class="eq-bar" style="animation-delay: 0.1s"></div>
        </div>
    </div>
    <div class="status-box">
        <div class="label">PROCESS LOAD</div>
        <div class="status-row">CPU <div class="bar-container"><div class="bar-fill" style="animation-duration: 3s"></div></div></div>
        <div class="status-row">MEM <div class="bar-container"><div class="bar-fill" style="animation-duration: 5s"></div></div></div>
        <div class="status-row">NET <div class="bar-container"><div class="bar-fill" style="animation-duration: 1.5s"></div></div></div>
    </div>
</div>

<script>
(function() {
    if (window.clockInterval) clearInterval(window.clockInterval);
    function updateClocks() {
        const now = new Date();
        const clocks = document.querySelectorAll('.time[data-timezone]');
        clocks.forEach(clock => {
            const tz = clock.getAttribute('data-timezone');
            try {
                clock.innerText = now.toLocaleTimeString('en-US', {
                    timeZone: tz, hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
                });
            } catch(e) { clock.innerText = "Error"; }
        });
        const randElement = document.getElementById('time-rand');
        if(randElement) randElement.innerText = Math.floor(Math.random() * 900000) + 100000;
    }
    const checkExist = setInterval(function() {
        const container = document.querySelector('.clock-container');
        if(container) {
            clearInterval(checkExist);
            updateClocks();
            window.clockInterval = setInterval(updateClocks, 100);
        }
    }, 200);
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
        example = None
        series = None
        status_msg = ""
        color = "#000000"
        
        bad_words = ["시발", "병신", "개새", "존나", "졸라", "충", "느금", "미친", "닥쳐", "씨발", "좆"] 
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

        with st.spinner("AI가 유행 패턴과 예문을 생성 중입니다..."):
            if text in KNOWN_SLANGS:
                months = KNOWN_SLANGS[text]
                llm_result = analyze_with_upstage(text)
                if llm_result:
                    example = llm_result.get('example') 
                _, series = generate_simulation_data(text, months)
            
            else:
                llm_result = analyze_with_upstage(text)
                if llm_result:
                    if llm_result.get('is_offensive'):
                        st.error("🚫 비속어 감지됨")
                        update_projector("#FF0000", "비속어", "result", "FILTERED")
                        st.stop()
                    
                    months = int(llm_result.get('months', 12))
                    example = llm_result.get('example') 
                    _, series = generate_simulation_data(text, months)
                else:
                    random.seed(hash(text))
                    months = random.randint(3, 60)
                    example = None
                    _, series = generate_simulation_data(text, months)

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
        
        if example:
            st.info(f"💬 AI가 만든 예문: \"{example}\"")
        
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
            st.plotly_chart(fig, use_container_width=True, theme=None, config={'displayModeBar': False})

        st.divider()
        if st.button("초기화 (대기모드)"):
            update_projector("#000000", "", "standby")
            del st.session_state.text
            st.rerun()

if __name__ == "__main__":
    main()
