import streamlit as st
import time
import json
import os

# --- 설정 ---
STATE_FILE = "state.json"
REFRESH_RATE = 0.5 

st.set_page_config(layout="wide", page_title="Visualizer")

# --- [NEW] 보색 계산 함수 ---
def get_complementary_color(hex_color):
    """
    주어진 HEX 색상의 보색을 계산하여 반환합니다.
    가독성을 높이기 위해 너무 어두운 보색은 밝게 조정합니다.
    """
    if not hex_color.startswith('#') or len(hex_color) != 7:
        return "#FFFFFF" # 기본값 흰색

    # HEX -> RGB 변환
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    # 보색 계산 (RGB 반전)
    comp_r, comp_g, comp_b = 255 - r, 255 - g, 255 - b
    
    # [가독성 튜닝] 만약 보색이 너무 어두우면(검정에 가까우면) 아예 밝은 색으로 대체
    if (comp_r + comp_g + comp_b) / 3 < 128:
         comp_r, comp_g, comp_b = 240, 240, 240

    # RGB -> HEX 변환
    return '#{:02x}{:02x}{:02x}'.format(comp_r, comp_g, comp_b)

# --- CSS: 손바닥 위 연출 ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap');

    .stApp {
        background-color: black;
        margin: 0;
        padding: 0;
        overflow: hidden;
    }
    header, footer {visibility: hidden;}
    
    .container {
        position: relative; /* 자식 요소 배치의 기준점 */
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        width: 100vw;
        overflow: hidden;
    }

    /* 빛의 구체 (Orb) - 배경 */
    .orb {
        position: absolute; 
        width: 70vh;
        height: 70vh;
        border-radius: 50%;
        filter: blur(40px);
        opacity: 0.9;
        animation: pulse 3s infinite ease-in-out;
        z-index: 1;
    }

    /* 텍스트 컨테이너 (선명함 유지) */
    .text-content {
        position: relative;
        z-index: 100;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }

    /* 메인 텍스트 (단어) */
    .main-text {
        font-family: 'Gowun Dodum', sans-serif;
        font-size: 8rem;
        font-weight: bold;
        margin-bottom: 20px;
        word-break: keep-all;
        -webkit-text-stroke: 2px black; 
    }

    /* 서브 텍스트 (개월 수) */
    .sub-text {
        font-family: 'Gowun Dodum', sans-serif;
        font-size: 3rem;
        font-weight: normal;
        -webkit-text-stroke: 1px black;
    }

    /* [NEW] 카운트다운용 스타일 */
    .countdown-num {
        font-family: 'Gowun Dodum', sans-serif;
        font-size: 15rem; /* 아주 큰 숫자 */
        font-weight: bold;
        color: white;
        text-shadow: 0 0 50px white;
        animation: blink-fast 0.5s infinite alternate; /* 깜빡거림 */
        z-index: 200;
    }

    .countdown-spinner {
        position: absolute;
        width: 60vh;
        height: 60vh;
        border-radius: 50%;
        border: 20px dashed rgba(255, 255, 255, 0.5); /* 점선 테두리 */
        border-top: 20px solid #00FFFF; /* 네온 시안 */
        border-bottom: 20px solid #FF00FF; /* 네온 마젠타 */
        animation: spin-fast 1s linear infinite; /* 빙글빙글 */
        filter: blur(5px);
        z-index: 150;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); opacity: 0.8; }
        50% { transform: scale(1.05); opacity: 1.0; }
        100% { transform: scale(0.95); opacity: 0.8; }
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* [NEW] 카운트다운용 빠른 회전 */
    @keyframes spin-fast {
        0% { transform: rotate(0deg) scale(1); }
        50% { transform: rotate(180deg) scale(1.1); }
        100% { transform: rotate(360deg) scale(1); }
    }

    /* [NEW] 카운트다운용 깜빡임 */
    @keyframes blink-fast {
        from { opacity: 1; transform: scale(1); }
        to { opacity: 0.5; transform: scale(0.9); }
    }
    
    .loading {
        border: 15px solid #333;
        border-top: 15px solid #fff;
        border-radius: 50%;
        width: 200px;
        height: 200px;
        animation: spin 1s linear infinite;
        z-index: 100;
    }

</style>
""", unsafe_allow_html=True)

def get_state():
    if not os.path.exists(STATE_FILE):
        return {"status": "standby", "color": "#000000", "text": "", "sub_text": ""}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"status": "standby", "color": "#000000", "text": "", "sub_text": ""}

state_placeholder = st.empty()

while True:
    state = get_state()
    status = state.get("status", "standby")
    color = state.get("color", "#000000")
    text = state.get("text", "")         # 메인 단어 (또는 카운트다운 숫자)
    sub_text = state.get("sub_text", "") # 개월 수
    
    # [NEW] 보색 계산
    comp_color = get_complementary_color(color)
    
    html_content = ""

    if status == "standby":
        html_content = f"""<div class="container" style="background-color: black;"></div>"""
        
    elif status == "listening":
        comp_listening = get_complementary_color(color)
        html_content = f"""
        <div class="container">
            <div class="orb" style="background: radial-gradient(circle, {color}, transparent); width: 30vh; height: 30vh;"></div>
            <div class="text-content">
                <div class="sub-text" style="font-size: 2rem; color: {comp_listening}; -webkit-text-stroke: 0px;">{text}</div>
            </div>
        </div>
        """

    elif status == "analyzing":
        html_content = f"""
        <div class="container">
            <div class="loading"></div>
            <div class="text-content">
                <div class="sub-text" style="margin-top: 30px; color: white; -webkit-text-stroke: 0px;">{text}</div>
            </div>
        </div>
        """

    elif status == "countdown":
        # [NEW] 카운트다운 모드
        # text 변수에 숫자가 들어옴 (5, 4, 3...)
        html_content = f"""
        <div class="container">
            <div class="countdown-spinner"></div>
            <div class="countdown-num">{text}</div>
        </div>
        """

    elif status == "result":
        html_content = f"""
        <div class="container">
            <div class="orb" style="
                background: radial-gradient(circle, {color} 0%, {color}44 70%, transparent 90%);
                box-shadow: 0 0 150px {color};">
            </div>
            <div class="text-content">
                <div class="main-text" style="color: {comp_color}; text-shadow: 0 0 30px {color}, 2px 2px 4px black;">{text}</div>
                <div class="sub-text" style="color: {comp_color}; text-shadow: 0 0 20px {color}, 1px 1px 2px black;">{sub_text}</div>
            </div>
        </div>
        """

    with state_placeholder.container():
        st.markdown(html_content, unsafe_allow_html=True)

    time.sleep(REFRESH_RATE)
