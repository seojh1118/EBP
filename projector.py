import streamlit as st
import time
import json
import os
import random

STATE_FILE = "state.json"
REFRESH_RATE = 0.5 

st.set_page_config(layout="wide", page_title="Fog Projector")

WORDS_DB = [
    "KIN", "안습", "지못미", "OTL", "킹왕짱", "우왕ㅋ굳ㅋ", "뭥미", "헐", 
    "방가방가", "하이루", "깜놀", "솔까말", "볼매", "훈남", "차도남", "엄친아", 
    "썩소", "레알", "듣보잡", "안물안궁", "간지", "대박", "캡", "짱",
    "즐", "고고씽", "냉무", "도촬", "불펌금지", "일촌", "파도타기", "도토리", 
    "먹방", "득템", "꿀팁", "멘붕", "썸", "최애", "입덕", "탈덕", "스펙", 
    "케미", "셀카", "ASMR", "인싸", "아싸", "만렙", "쪼렙", "흑역사", "정주행", 
    "럭키비키", "완전럭키비키잖아", "사고다", "너T야?", "중꺾마", "폼미쳤다", 
    "알빠노", "갓생", "분좋카", "캘박", "저메추", "점메추", "스불재", "도파민", 
    "잼얘", "젠지", "킹받네", "어쩔티비", "뇌절", "억까", "억빠", "갓기"
]

st.markdown("""
<style>
    /* 폰트: 굵고 단순한 것 */
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic+Coding:wght@700&display=swap');
    
    .stApp {
        background-color: black;
        margin: 0; padding: 0;
        overflow: hidden; /* 스크롤바 제거 */
    }
    header, footer { visibility: hidden; }
    
    /* 1. 전체 화면 색상 박스 (Result, Standby, Listening 용) */
    .full-screen-color {
        position: fixed;
        top: 0; left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 100;
        transition: background-color 1s ease; /* 색상 부드럽게 변경 */
    }

    /* 2. 분석 중일 때 나오는 폭포수 컨테이너 */
    .torrent-container {
        position: fixed;
        top: 0; left: 0;
        width: 100vw;
        height: 120vh; /* 화면보다 길게 */
        background-color: #000;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        align-items: center;
        z-index: 200;
        animation: scrollUp 1.5s linear infinite; /* 빠르게 올라감 */
        opacity: 0.9;
    }

    /* 말풍선 스타일 (포그 위에서도 잘 보이게 형광색 위주) */
    .chat-bubble {
        font-family: 'Nanum Gothic Coding', monospace;
        font-size: 4rem; /* 글자 아주 크게 */
        font-weight: 900;
        padding: 10px 40px;
        margin: 10px;
        border-radius: 50px;
        width: fit-content;
        box-shadow: 0 0 20px currentColor; /* 빛 번짐 효과 */
        text-shadow: 0 0 10px white;
    }
    
    .bubble-left {
        align-self: flex-start;
        margin-left: 5%;
        color: #00FF00; /* 네온 그린 */
        border: 5px solid #00FF00;
        background: rgba(0, 255, 0, 0.1);
    }
    
    .bubble-right {
        align-self: flex-end;
        margin-right: 5%;
        color: #FF00FF; /* 네온 핑크 */
        border: 5px solid #FF00FF;
        background: rgba(255, 0, 255, 0.1);
    }

    @keyframes scrollUp {
        0% { transform: translateY(0); }
        100% { transform: translateY(-20%); }
    }

</style>
""", unsafe_allow_html=True)

def get_state():
    if not os.path.exists(STATE_FILE):
        return {"status": "standby", "color": "#000000", "text": ""}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"status": "standby", "color": "#000000", "text": ""}


def render_solid_color(hex_color):
    """화면 전체를 색상으로 꽉 채움 (텍스트 없음)"""
    return f'<div class="full-screen-color" style="background-color: {hex_color};"></div>'

def render_analyzing_torrent(target_text):
    """분석 중: 거대한 글자들이 폭포처럼 쏟아짐"""
    html = '<div class="torrent-container">'

    for _ in range(20):
        
        if random.random() > 0.7 and target_text:
            word = target_text
        else:
            word = random.choice(WORDS_DB)
            
        is_right = random.choice([True, False])
        cls = "bubble-right" if is_right else "bubble-left"
        
        html += f'<div class="chat-bubble {cls}">{word}</div>'
        
    html += '</div>'
    return html

def render_countdown():
    """카운트다운: 흰색 깜빡임 (Strobe 효과)"""

    return '<div class="full-screen-color" style="background-color: #FFFFFF; animation: blink 0.2s infinite;"></div>'


state_placeholder = st.empty()

while True:
    state = get_state()
    status = state.get("status", "standby")
    color = state.get("color", "#000000") 
    text = state.get("text", "")

    html_content = ""

    if status == "analyzing":

        html_content = render_analyzing_torrent(text)
        
    elif status == "countdown":

        html_content = '<div class="full-screen-color" style="background-color: #FFFFFF;"></div>'
        
    else:

        html_content = render_solid_color(color)

    with state_placeholder.container():
        st.markdown(html_content, unsafe_allow_html=True)
        
    time.sleep(REFRESH_RATE)
