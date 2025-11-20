import streamlit as st
import speech_recognition as sr
import pandas as pd
import numpy as np
from pytrends.request import TrendReq
import datetime
import time
import random 
import joblib # 모델/스케일러 로드용
from sklearn.metrics.pairwise import euclidean_distances # '유사 단어' 계산용
import requests # API 호출용
import xml.etree.ElementTree as ET 

# -----------------------------------------------------------
# [기능 1] 표준어 판별 함수 (국립국어원 API)
# -----------------------------------------------------------
def check_is_standard_word(word):
    """
    국립국어원 표준국어대사전 API를 조회하여
    해당 단어가 '표준어'인지(사전에 등재되어 있는지) 확인합니다.
    """
    # 🔑 발급받은 API 키
    API_KEY = "C39F8A5DC5EEAE06C1307EDF6450E52B" 
    
    url = "https://stdict.korean.go.kr/api/search.do"
    
    params = {
        "key": API_KEY,
        "q": word,
        "req_type": "json",
        "advanced": "y",    
        "method": "exact"   
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and 'channel' in data and 'total' in data['channel']:
                count = int(data['channel']['total'])
                if count > 0:
                    return True # 표준어임
        return False # 사전에 없음 (신조어)
    except Exception:
        return False

# -----------------------------------------------------------
# [기능 2] 4-Feature 모델 및 데이터 로드
# -----------------------------------------------------------
@st.cache_resource
def load_assets():
    try:
        # 1. 4-feature로 훈련된 파일 로드 (파일명 확인 필수)
        knn_model = joblib.load('knn_model.pkl')
        scaler = joblib.load('scaler.pkl')
        
        # 2. 4-feature가 포함된 CSV 로드
        df = pd.read_csv('final_training_dataset.csv')
        df_train = df[df['Lifetime (Months)'] != 'Ongoing'].copy()
        
        # 3. [핵심] 모델이 학습한 피처 4개 (순서 일치 필수)
        features = ['Word_Length', 'Max_Rising_Slope', 'Initial_Volatility', 'Initial_Decay_Rate']
        
        # NaN 값 처리 (훈련 시와 동일하게 0으로 대체)
        for col in features:
             if col in df_train.columns:
                 df_train[col] = df_train[col].fillna(0)
        
        # 4. '유사 단어' 비교를 위해 스케일링된 훈련 데이터 X 준비
        X_train_scaled = scaler.transform(df_train[features])
        
        # 5. 유사 단어의 '이름' 목록
        Word_names = df_train['Word'].values
        
        return df_train, knn_model, scaler, X_train_scaled, Word_names, features
    
    except FileNotFoundError:
        st.error("❌ ERROR: 데이터 파일을 찾을 수 없습니다.")
        st.info("lifetime_calculator.py와 k_nn_model.py를 먼저 실행하여 4-Feature 데이터를 생성하세요.")
        return None, None, None, None, None, None
    except Exception as e:
        st.error(f"❌ 모델 로드 중 오류: {e}")
        return None, None, None, None, None, None

# -----------------------------------------------------------
# [기능 3] 4-Feature 실시간 계산 함수 (Data Leakage 방지)
# -----------------------------------------------------------
def get_realtime_features(word):
    """
    입력된 단어의 '최근 1년치' 데이터를 가져와 
    '초기 단서' 피처 4개를 계산합니다.
    """
    try:
        pytrends = TrendReq(hl='ko-KR', tz=540)
        time.sleep(1 + random.uniform(0, 2)) # 429 방지용 딜레이

        # [핵심] 1년치 데이터만 요청 (미래 정보 배제)
        today = datetime.date.today()
        one_year_ago = today - datetime.timedelta(days=365)
        timeframe = f'{one_year_ago.strftime("%Y-%m-%d")} {today.strftime("%Y-%m-%d")}'
        
        pytrends.build_payload([word], cat=0, timeframe=timeframe, geo='KR')
        interest_df = pytrends.interest_over_time()
        
        if interest_df.empty or word not in interest_df.columns:
            st.warning(f"'{word}'에 대한 (최근 1년) 트렌드 데이터가 충분하지 않습니다.")
            return None, None
            
        series = interest_df[word]
        
    except Exception as e:
        if "429" in str(e):
            st.error("❌ Google Trends 요청 한도를 초과했습니다 (429 Error). 1분 후 다시 시도해주세요.")
        else:
            st.error(f"트렌드 데이터 수집 중 오류: {e}")
        return None, None

    # --- 4-Feature 계산 로직 ---
    # 1. Word_Length
    word_len = len(word.replace(" ", ""))

    # 2. Max_Rising_Slope
    slopes = series.diff().fillna(0)
    max_rising_slope = slopes[slopes > 0].max()
    max_rising_slope = 0 if pd.isna(max_rising_slope) else max_rising_slope
    
    # 3. Initial_Volatility (초기 변동성)
    initial_volatility = series.std()
    initial_volatility = 0 if pd.isna(initial_volatility) else initial_volatility
    
    # 4. Initial_Decay_Rate (초기 하락 속도)
    peak_index = series.idxmax()
    after_peak_series = series.loc[peak_index:]
    initial_decay_rate = 0
    if len(after_peak_series) > 1:
        initial_decay_rate = after_peak_series.mean()
        initial_decay_rate = 0 if pd.isna(initial_decay_rate) else initial_decay_rate

    # 4가지 피처 리스트 반환
    final_features = [word_len, max_rising_slope, initial_volatility, initial_decay_rate]
    
    return final_features, series

# --- STT 및 UI 함수 ---
def on_stt_button_click():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 마이크에 대고 말씀하세요... (3초간 녹음)")
        try:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
            text = r.recognize_google(audio, language='ko-KR')
            st.session_state.text = text 
            st.success(f"✅ \"{text}\" 음성 인식 성공!")
        except sr.WaitTimeoutError:
            st.warning("⚠️ 음성 입력 시간이 초과되었습니다.")
        except sr.UnknownValueError:
            st.error("❌ 음성을 인식할 수 없습니다.")
        except Exception as e:
            st.error(f"❌ 오류: {e}")

def load_css(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except:
        pass

# --- 메인 실행 함수 ---
def main():
    load_css("style.css")
    
    try:
        st.video("img/smoke.mp4", start_time=0)
    except:
        pass # 영상 없으면 패스

    st.markdown('<h1 class="title-text"><span>☯︎단어 멸망 시계☯︎</span></h1>', unsafe_allow_html=True)
    st.markdown("<p>음성으로 신조어를 입력하면, 4가지 '초기 유행 패턴'을 분석하여 수명을 예측합니다.</p>", unsafe_allow_html=True)

    # 1. 자산 로드
    assets = load_assets()
    df_train, knn_model, scaler, X_train_scaled, Word_names, features_list = assets
    
    if knn_model is None:
        return 

    # 2. STT 버튼
    st.button("Click to Speak", on_click=on_stt_button_click, use_container_width=True)

    # 3. 실행 로직
    if "text" in st.session_state and st.session_state.text:
        text = st.session_state.text
        st.markdown(f"<p class='user-input'>입력된 단어: \"{text}\"</p>", unsafe_allow_html=True)

        # ---------------------------------------------------------
        # [단계 1] 표준어(영생) 판별
        # ---------------------------------------------------------
        is_standard = check_is_standard_word(text)

        if is_standard:
            st.balloons()
            st.success(f"✨ '{text}'은(는) 표준국어대사전에 등재된 '표준어'입니다.")
            st.markdown(f"""
                <div class='result-text' style='color: #4CAF50; font-size: 40px;'>
                    ♾️ 영생 (Immortal)
                </div>
                <p class='sub-text' style='margin-top: 10px;'>
                    이 단어는 유행을 타지 않고, 우리가 사용하는 언어로서<br>
                    <b>영원히 생명력을 유지할 것</b>입니다.
                </p>
            """, unsafe_allow_html=True)
            del st.session_state.text
            st.stop() 

        # ---------------------------------------------------------
        # [단계 2] 신조어 수명 예측 (표준어가 아닐 경우)
        # ---------------------------------------------------------
        live_features = None 
        live_series = None   
        is_new_word = False
        
        try:
            # (A) 하이브리드 로직: DB 우선 검색
            word_data_from_db = df_train[df_train['Word'] == text]
            
            if not word_data_from_db.empty:
                st.info("💡 학습된 단어입니다. 저장된 데이터로 분석합니다.")
                # DB에서 4개 피처 로드
                live_features = word_data_from_db[features_list].values.tolist()[0]
                is_new_word = False
            else:
                # (B) 신조어: API 호출 (4개 피처 계산)
                with st.spinner(f"신조어 '{text}'의 '초기 1년 패턴'을 실시간 분석 중..."):
                    live_features, live_series = get_realtime_features(text) 
                is_new_word = True

            if live_features is None:
                st.error("데이터를 분석할 수 없습니다.")
                del st.session_state.text 
                st.stop() 
            
            # (C) 예측 및 스케일링
            word_len, max_slope, volatility, decay_rate = live_features # 4개 언패킹
            
            X_live_scaled = scaler.transform(np.array([live_features]))
            predicted_lifetime = knn_model.predict(X_live_scaled)
            predicted_months = int(np.round(predicted_lifetime[0]))
            
            # (D) 유사 단어 찾기 (4차원 거리)
            K = 5
            distances = euclidean_distances(X_live_scaled, X_train_scaled).flatten()
            
            if is_new_word:
                nearest_indices = np.argsort(distances)[:K]
            else:
                nearest_indices = np.argsort(distances)[1:K+1]
                
            nearby_words_list = Word_names[nearest_indices]

            # (E) 결과 표시
            st.success(f"✅ '{text}'의 '초기 패턴' 분석 완료!")
            
            # [디펜스] 4가지 피처 수치 표시
            st.markdown(f"""
                > (길이: **{word_len}**, 초기 기울기: **{max_slope:.2f}**, 
                초기 변동성: **{volatility:.2f}**, 초기 하락 속도: **{decay_rate:.2f}**)
            """)
            
            if is_new_word and live_series is not None:
                st.info(f"'{text}'의 최근 1년 트렌드")
                st.line_chart(live_series)

            st.subheader('🕰️ 예측된 멸망까지 남은 시간')
            
            result_message = f"{predicted_months} 개월"
            status_text = "..." 
            if predicted_months <= 6 and predicted_months > 0:
                 result_message = f'<span style="color: red;">{predicted_months} 개월</span>'
                 status_text = "🚨 소멸 임박! 급격한 하락 추세입니다."
            elif predicted_months == 0:
                 result_message = '<span>소멸 완료</span>'
                 status_text = "💀 유행이 끝났습니다."
            else:
                 result_message = f'<span style="color: #007BFF;">{predicted_months} 개월</span>'
                 status_text = "📈 아직 생명력을 유지하고 있습니다."

            # 카운트다운
            result_placeholder = st.empty()
            start_tick = 60 
            if predicted_months > start_tick:
                start_point = start_tick
            else:
                start_point = max(predicted_months + 10, predicted_months)
            
            for i in range(start_point, predicted_months - 1, -1):
                result_placeholder.markdown(f"<div class=\"result-text\">{i}</div>", unsafe_allow_html=True)
                time.sleep(0.05) 

            result_placeholder.markdown(f"<div class=\"result-text\">{result_message}</div>", unsafe_allow_html=True)
            
            # [디펜스] 4-Feature 논리 설명
            st.markdown(f'<p class="sub-text" style="color: #AAA;">{status_text}</p>', unsafe_allow_html=True)
            st.markdown(f"""
                <p style='font-size: 16px; color: #E0E0E0;'>
                (예측 근거: <b>'{text}'</b>의 '초기 4대 유행 패턴'을
                기존 단어 (<b>{', '.join(nearby_words_list)}</b> 등)의 
                패턴과 비교하여 수명을 예측)
                </p>
            """, unsafe_allow_html=True)

        except Exception as e:
            if "429" in str(e):
                st.error("❌ Google Trends 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
            else:
                st.error(f"❌ 오류 발생: {e}")
        
        del st.session_state.text

if __name__ == "__main__":
    st.set_page_config(page_title="단어 멸망 시계", layout="centered") 
    main()

# 안개 효과 CSS
st.markdown("""
<div class="fog-container">
  <div class="fog-img fog-img-first"></div>
  <div class="fog-img fog-img-second"></div>
</div>
""", unsafe_allow_html=True)