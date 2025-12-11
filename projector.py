import streamlit as st
import time
import json
import os
import random

STATE_FILE = "state.json"
REFRESH_RATE = 0.5 

st.set_page_config(layout="wide", page_title="Hologram Projector")

WORDS_DB = [
    "KIN", "안습", "지못미", "OTL", "킹왕짱", "우왕ㅋ굳ㅋ", "뭥미", "헐", 
    "방가방가", "하이루", "깜놀", "솔까말", "볼매", "훈남", "차도남", "엄친아", 
    "썩소", "레알", "듣보잡", "안물안궁", "간지", "대박", "캡", "짱",
    "즐", "고고씽", "냉무", "도촬", "불펌금지", "일촌", "파도타기", "도토리", 
    "스크랩", "얼짱", "생얼", "완소", "베프", "훈녀", "루저", "잉여", 
    "크리", "넘사벽", "흠좀무", "리즈시절","개드립", "품절남", "품절녀",
    "눈팅", "염장", "뽐뿌", "득햏", "아햏햏", "방법", "버로우", "잠수", "정모", "번개",
    "짤방", "움짤", "직찍", "뽀샵", "본방사수", "레어템", "지름신", "엄크",
    "광클", "스압", "개이득", "반사", "무지개반사", "초딩", "딩초", "즐겜", "매너겜",
    "먹방", "득템", "꿀팁", "멘붕", "썸", "최애", "입덕", "탈덕", "스펙", 
    "케미", "셀카", "ASMR", "인싸", "아싸", "만렙", "쪼렙", "흑역사", "정주행", 
    "스포", "남사친", "여사친", "심쿵", "꽃길", "1도없다", "소확행", "워라밸", 
    "TMI", "갑질", "꼰대", "비주얼", "가성비", "팩트폭행", "사이다", "고구마", 
    "혼밥", "혼술", "배달", "언박싱", "역주행", "뇌피셜", "국룰", "본캐", "부캐", 
    "티키타카", "빌런", "플렉스", "멍때리기", "치팅데이", "루틴", "알잘딱깔센",
    "갑분싸", "이불킥", "현타", "동공지진", "세젤예", "졸귀", "핵노잼", "꿀잼", 
    "인생샷", "프사", "배사", "단톡방", "읽씹", "안읽씹", "랜선이모", "랜선집사",
    "댕댕이", "냥이", "띵곡", "띵작", "케바케", "사바사", "법블레스유", "할말하않",
    "워킹맘", "육아대디", "경단녀", "나일론환자", "뇌섹남", "요섹남", "금수저", "흙수저",
    "럭키비키", "완전럭키비키잖아", "사고다", "너T야?", "중꺾마", "폼미쳤다", 
    "알빠노", "갓생", "분좋카", "캘박", "저메추", "점메추", "스불재", "도파민", 
    "잼얘", "젠지", "킹받네", "어쩔티비", "뇌절", "억까", "억빠", "갓기", 
    "삼귀다", "쫌쫌따리", "오우예", "추구미", "기제", "가보자고", "무물", 
    "좋아요정", "반모", "반신", "구취", "핑프", "할매니얼", "디토", "힙하다", 
    "성덕", "주불", "갓성비", "나심비", "영끌", "빚투", "복세편살", "마상", 
    "자만추", "인만추", "갓심비", "꾸꾸꾸", "꾸안꾸", "머선129", "700",
    "오히려좋아", "가불기", "킹리적갓심", "킹정", "킹아", "갓벽", "완내스", "제당슈만",
    "얼죽아", "뜨죽아", "군싹", "오운완", "밈", "숏폼", "릴스", "챌린지", "디깅",
    "식집사", "냥아치", "댕청", "커엽", "H워얼V", "쌉가능", "당모치", "민초단", "찍먹", "부먹"
]

RETRO_COLORS = [
    "#FF0055", "#00EEFF", "#39FF14", "#FFE600", "#FF5F00", "#CC00FF", "#FFFFFF"
]
def get_complementary_color(hex_color):
    if not hex_color.startswith('#') or len(hex_color) != 7: return "#FFFFFF"
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    comp_r, comp_g, comp_b = 255 - r, 255 - g, 255 - b
    if (comp_r + comp_g + comp_b) / 3 < 128: comp_r, comp_g, comp_b = 240, 240, 240
    return '#{:02x}{:02x}{:02x}'.format(comp_r, comp_g, comp_b)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=Nanum+Gothic+Coding:wght@700&display=swap');
            
    .stApp { background-color: black; overflow: hidden; }
    header, footer { visibility: hidden; }
    
    .container {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        display: flex; justify-content: center; align-items: center;
        overflow: hidden; pointer-events: none;
    }

    .ghost-word {
        position: absolute;
        font-family: 'Nanum Gothic Coding', monospace;
        font-weight: bold;
        padding: 5px 10px;
        border: 2px solid;
        background: rgba(0,0,0,0.5);
        box-shadow: 0 0 10px currentColor;
        opacity: 0;
        animation: floatAndFade 6s infinite ease-in-out;
    }
    
    @keyframes floatAndFade {
        0% { opacity: 0; transform: translateY(50px) scale(0.8); }
        20% { opacity: 0.8; transform: translateY(0px) scale(1); }
        80% { opacity: 0.8; transform: translateY(-50px) scale(1); }
        100% { opacity: 0; transform: translateY(-100px) scale(0.8); }
    }

    .torrent-container {
        position: absolute; width: 100%; height: 120%;
        display: flex; flex-direction: column; justify-content: flex-end; align-items: center;
        animation: scrollUp 2s linear infinite;
    }
    
    .chat-bubble {
        background-color: #333; color: #00FF00;
        padding: 10px 20px; margin: 5px; border-radius: 20px;
        font-family: 'Nanum Gothic Coding', monospace; font-size: 1.5rem;
        border: 1px solid #00FF00; box-shadow: 0 0 5px #00FF00;
        width: fit-content; max-width: 80%;
    }
    
    .chat-bubble.me {
        align-self: flex-end; background-color: #004400; margin-right: 10%;
    }
    .chat-bubble.other {
        align-self: flex-start; background-color: #222; margin-left: 10%;
    }

    @keyframes scrollUp {
        0% { transform: translateY(0); }
        100% { transform: translateY(-20%); }
    }

    .orb-container {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        z-index: 10;
    }
    .orb {
        width: 60vh; height: 60vh; border-radius: 50%;
        filter: blur(30px); opacity: 0.9;
        animation: pulse 3s infinite ease-in-out;
        display: flex; align-items: center; justify-content: center;
        background: radial-gradient(circle, var(--orb-color) 0%, transparent 70%);
        box-shadow: 0 0 100px var(--orb-color);
    }
    .orb-text {
        font-family: 'Gowun Dodum', sans-serif; text-align: center;
        z-index: 20; position: absolute;
    }
    .main-text {
        font-size: 6rem; font-weight: bold;
        text-shadow: 0 0 20px black; -webkit-text-stroke: 2px black;
        margin-bottom: 1rem;
    }
    .sub-text {
        font-size: 3rem; font-weight: bold;
        text-shadow: 0 0 10px black; -webkit-text-stroke: 1px black;
    }

    .countdown-num {
        font-size: 15rem; font-weight: bold; color: white;
        text-shadow: 0 0 50px white;
        animation: blink 0.5s infinite alternate;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); opacity: 0.8; }
        50% { transform: scale(1.05); opacity: 1.0; }
        100% { transform: scale(0.95); opacity: 0.8; }
    }
    @keyframes blink { from { opacity: 1; } to { opacity: 0.5; } }

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

def render_standby_ghosts():
    html = '<div class="container">'
    sample_words = random.sample(WORDS_DB, 15)
    for word in sample_words:
        top = random.randint(10, 80)
        left = random.randint(10, 80)
        color = random.choice(RETRO_COLORS)
        delay = random.uniform(0, 5) 
        duration = random.uniform(4, 8)
        
        style = f"top: {top}%; left: {left}%; color: {color}; border-color: {color}; animation-delay: -{delay}s; animation-duration: {duration}s;"
        html += f'<div class="ghost-word" style="{style}">{word}</div>'
    html += '</div>'
    return html

def render_analyzing_torrent(current_text):
    html = '<div class="container"><div class="torrent-container">'

    for _ in range(30):
        is_me = random.choice([True, False])
        word = current_text if random.random() > 0.7 else random.choice(WORDS_DB)
        cls = "me" if is_me else "other"
        html += f'<div class="chat-bubble {cls}">{word}</div>'
        
    html += '</div></div>'
    return html

def render_result_orb(text, sub_text, color, is_countdown=False):
    comp_color = get_complementary_color(color)
    
    content = ""
    if is_countdown:
        content = f'<div class="countdown-num">{text}</div>'
    else:
        content = f"""
        <div class="orb-text">
            <div class="main-text" style="color:{comp_color};">{text}</div>
            <div class="sub-text" style="color:{comp_color};">{sub_text}</div>
        </div>
        """
        
    html = f"""
    <div class="container">
        <div class="orb" style="--orb-color: {color};">
            {content}
        </div>
    </div>
    """
    return html

state_placeholder = st.empty()

while True:
    state = get_state()
    status = state.get("status", "standby")
    color = state.get("color", "#000000")
    text = state.get("text", "")
    sub_text = state.get("sub_text", "")

    html_content = ""

    if status == "standby":
        html_content = render_standby_ghosts()

    elif status == "listening":
        html_content = render_result_orb("듣고 있어요...", "말씀해주세요", "#FFFF00")

    elif status == "analyzing":
        html_content = render_analyzing_torrent(text)

    elif status == "countdown":
        html_content = render_result_orb(text, "", "#FFFFFF", is_countdown=True)

    elif status == "result":
        html_content = render_result_orb(text, sub_text, color)

    with state_placeholder.container():
        st.markdown(html_content, unsafe_allow_html=True)
    time.sleep(REFRESH_RATE)
