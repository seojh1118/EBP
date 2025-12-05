import streamlit as st
import time
import json
import os

# --- 설정 ---
STATE_FILE = "state.json"
REFRESH_RATE = 0.5 # 0.5초마다 상태 확인

st.set_page_config(layout="wide", page_title="Visualizer")

# --- CSS: 손바닥 위 연출을 위한 특수 효과 ---
st.markdown("""
<style>
    /* 전체 화면 검은색 처리 및 여백 제거 */
    .stApp {
        background-color: black;
        margin: 0;
        padding: 0;
    }
    header, footer {visibility: hidden;}
    
    /* 중앙 정렬 컨테이너 */
    .container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        width: 100vw;
        overflow: hidden;
    }

    /* 빛의 구체 (Orb) - 손바닥 위에 맺힐 빛 */
    .orb {
        width: 60vh;
        height: 60vh;
        border-radius: 50%;
        filter: blur(30px); /* 포그 안에서 몽환적으로 퍼지게 */
        opacity: 0.8;
        animation: pulse 3s infinite ease-in-out;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    /* 텍스트 (개월 수) */
    .text {
        font-family: 'Courier New', monospace;
        font-size: 5rem;
        font-weight: bold;
        color: white;
        text-shadow: 0 0 20px black;
        z-index: 10;
    }

    /* 숨쉬기 애니메이션 */
    @keyframes pulse {
        0% { transform: scale(0.9); opacity: 0.7; }
        50% { transform: scale(1.1); opacity: 0.9; }
        100% { transform: scale(0.9); opacity: 0.7; }
    }
    
    /* 회전 애니메이션 (분석 중일 때) */
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .loading {
        border: 10px solid #333;
        border-top: 10px solid #fff;
        border-radius: 50%;
        width: 200px;
        height: 200px;
        animation: spin 1s linear infinite;
    }

</style>
""", unsafe_allow_html=True)

# --- 상태 읽기 ---
def get_state():
    if not os.path.exists(STATE_FILE):
        return {"status": "standby", "color": "#000000", "text": ""}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"status": "standby", "color": "#000000", "text": ""}

# --- 메인 루프 ---
state_placeholder = st.empty()

while True:
    state = get_state()
    status = state.get("status", "standby")
    color = state.get("color", "#000000")
    text = state.get("text", "")
    
    html_content = ""

    if status == "standby":
        # 대기: 완전한 어둠 (포그만 흐르게)
        html_content = f"""
        <div class="container" style="background-color: black;">
        </div>
        """
        
    elif status == "listening":
        # 듣는 중: 희미한 노란 빛
        html_content = f"""
        <div class="container">
            <div class="orb" style="background: radial-gradient(circle, {color}, transparent); width: 30vh; height: 30vh;"></div>
        </div>
        """

    elif status == "analyzing":
        # 분석 중: 회전하는 로딩
        html_content = f"""
        <div class="container">
            <div class="loading"></div>
        </div>
        """

    elif status == "result":
        # 결과 출력: 강렬한 색상의 빛 + 텍스트
        # background: radial-gradient... 이 부분이 핵심입니다.
        # 중심은 진한 색 -> 바깥으로 갈수록 투명해져서 손바닥 위에 자연스럽게 얹힙니다.
        html_content = f"""
        <div class="container">
            <div class="orb" style="
                background: radial-gradient(circle, {color} 0%, {color}44 60%, transparent 80%);
                box-shadow: 0 0 100px {color};">
                <div class="text">{text}</div>
            </div>
        </div>
        """

    with state_placeholder.container():
        st.markdown(html_content, unsafe_allow_html=True)

    time.sleep(REFRESH_RATE)
    # Streamlit 특성상 루프 안에서 UI 갱신하려면 rerun 필요할 수 있음
    # 하지만 st.empty() + while 루프가 더 부드러울 수 있음
    # 만약 갱신 안되면 아래 주석 해제
    st.rerun()