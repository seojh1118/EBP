import streamlit as st
import speech_recognition as sr
import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsRegressor
import time
from pytrends.request import TrendReq
import datetime 

def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"❌ ERROR: 'style.css' 파일을 찾을 수 없습니다. app.py와 같은 폴더에 있는지 확인하세요.")

st.set_page_config(page_title="단어 멸망 시계", layout="centered")
load_css("style.css")

# --- 1. 모델 및 데이터 로드 (Streamlit 캐싱 사용) ---
@st.cache_resource
def load_model_and_data():
    try:
        df = pd.read_csv('final_training_dataset.csv')
        df_train = df[df['Lifetime (Months)'] != 'Ongoing'].copy()
        
        # 'Max_Rising_Slope'에 결측치(NaN)가 있으면 0으로 채움
        df_train['Max_Rising_Slope'] = df_train['Max_Rising_Slope'].fillna(0)
        
        # Y축: 수명 (숫자형)
        Y_train = df_train['Lifetime (Months)'].astype(int)
        
        # 🔽 X축: 입력 피쳐 (변경됨)
        X_train = df_train[['Max_Rising_Slope']] 
        
        knn_model = KNeighborsRegressor(n_neighbors=3)
        knn_model.fit(X_train, Y_train)
        
        return knn_model, df_train
        
    except FileNotFoundError:
        st.error("❌ ERROR: 'final_training_dataset.csv' 파일을 찾을 수 없습니다. lifetime_calculator.py를 실행하세요.")
        return None, None
    except Exception as e:
        st.error(f"❌ ERROR: 모델 로드 중 오류 발생: {e}")
        return None, None

# --- 2. [신규] 실시간 '최대 상승 기울기' 계산 함수 ---
def calculate_realtime_slope(word_series, word):
    """
    pytrends로 가져온 실시간 pandas.Series를 분석하여 
    '최대 상승 기울기(Max_Rising_Slope)'를 계산합니다.
    (lifetime_calculator.py 로직 기반)
    """
    try:
        # 1. 정점(Peak) 찾기
        peak_value = word_series.max()
        if peak_value == 0:
            return 0.0 # 유행 기록 없음
        
        peak_date_index = word_series.idxmax()

        # 2. 유행 시작점(Start) 찾기
        start_threshold = peak_value * 0.1 # 최대치의 10%
        start_index = word_series[word_series >= start_threshold].first_valid_index()

        # 3. 최대 상승 기울기 계산
        max_rising_slope = 0.0 # 기본값
        
        if start_index is not None and start_index < peak_date_index:
            # 상승 구간 (시작점 ~ 정점)
            rising_period = word_series.loc[start_index:peak_date_index]
            
            if len(rising_period) > 1:
                # 월별 관심도 변화율(diff)의 최대값
                max_slope = rising_period.diff().max()
                
                # NaN이 아닐 경우에만 값 할당
                if not pd.isna(max_slope):
                    max_rising_slope = max_slope
        
        # 0보다 작은 값은 0으로 처리 (하락은 무시)
        return max(0.0, max_rising_slope)

    except Exception as e:
        st.error(f"'{word}' 기울기 계산 중 오류: {e}")
        return 0.0 # 오류 시 0 반환

# --- 3. [수정됨] 예측 함수 (기울기 값을 X로 받음) ---
def predict_lifetime(model, df_train, slope_value):
    """
    계산된 '기울기' 값을 받아 k-NN 모델로 수명을 예측합니다.
    """
    # 1. X 피쳐 생성 (DataFrame 형태)
    X_pred = pd.DataFrame({'Max_Rising_Slope': [slope_value]})
    
    # 2. k-NN 모델로 예측
    predicted_lifetime = model.predict(X_pred)
    
    # 3. 예측값 반환 (정수로 반올림)
    final_months = int(round(predicted_lifetime[0]))
    
    # 4. 예측에 사용된 '가까운' 단어(이웃) 찾기
    distances, indices = model.kneighbors(X_pred)
    nearby_words = df_train.iloc[indices[0]]['Word'].tolist()

    return final_months, nearby_words


# --- 4. 음성 인식 콜백 함수 (STT) (기존과 동일) ---
def on_stt_button_click():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 마이크에 대고 말씀하세요... (3초간 녹음)")
        try:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
            
            # STT (Google)
            text = r.recognize_google(audio, language='ko-KR')
            st.session_state.text = text # 세션에 저장
            st.success(f"✅ \"{text}\" 음성 인식 성공!")
            
        except sr.WaitTimeoutError:
            st.warning("⚠️ 음성 입력 시간이 초과되었습니다.")
        except sr.UnknownValueError:
            st.error("❌ 음성을 인식할 수 없습니다.")
        except sr.RequestError as e:
            st.error(f"❌ Google STT 서비스 오류: {e}")
        except Exception as e:
            st.error(f"❌ STT 처리 중 알 수 없는 오류: {e}")

def main():
    load_css("style.css")
    st.video("img/smoke.mp4", start_time=0)
    st.markdown('<h1 class="title-text"><span>☯︎단어 멸망 시계☯︎</span></h1>', unsafe_allow_html=True)
    st.markdown("<p>음성으로 신조어를 입력하면, '최대 상승 기울기'를 실시간 분석하여 수명을 예측합니다.</p>", unsafe_allow_html=True)

    # 1. 모델 로드
    knn_model, df_train = load_model_and_data()
    if knn_model is None:
        return # 모델 로드 실패 시 중단

    # 2. STT 버튼
    st.button("Click to Speak", on_click=on_stt_button_click, use_container_width=True)

    # 3. [수정됨] STT 완료 후 '실시간 분석' 및 '예측' 로직
    if "text" in st.session_state and st.session_state.text:
        text = st.session_state.text
        st.markdown(f"<p class='user-input'>입력된 단어: \"{text}\"</p>", unsafe_allow_html=True)

        realtime_slope = 0.0
        interest_df = None
        
        try:
            # --- (A) [신규] 실시간 Pytrends 호출 ---
            with st.spinner(f"Google Trends에서 '{text}'의 트렌드 데이터를 실시간 분석 중..."):
                pytrends = TrendReq(hl='ko-KR', tz=540)
                pytrends.build_payload([text], cat=0, timeframe='all', geo='KR')
                interest_df = pytrends.interest_over_time()

            if interest_df.empty or text not in interest_df.columns:
                st.error(f"'{text}'에 대한 Google Trends 데이터를 찾을 수 없습니다.")
                del st.session_state.text # 세션 초기화
                return # 중단

            # --- (B) [신규] 실시간 기울기 계산 ---
            word_series = interest_df[text]
            realtime_slope = calculate_realtime_slope(word_series, text)
            
            st.success(f"✅ '{text}'의 '최대 상승 기울기' 계산 완료: **{realtime_slope:.2f}**")
            
            # (선택) 실시간 차트 표시
            st.line_chart(word_series)

            # --- (C) [수정됨] 기울기 기반 예측 ---
            predicted_months, nearby_words_list = predict_lifetime(knn_model, df_train, realtime_slope)

            # --- (D) [기존] 카운트다운 로직 (동일하게 사용) ---
            
            # 결과 메시지 설정 (기존 로직과 동일)
            result_message = f"{predicted_months} 개월"
            status_text = "📈 아직 생명력을 유지하고 있습니다." # (기존 로직 단순화)
            
            # 1. 숫자가 표시될 빈 공간(Placeholder) 생성
            result_placeholder = st.empty()
            
            # 2. 카운트다운 시작 (예: 60부터)
            start_tick = 60 
            
            # 3. 60부터 예측된 수명(predicted_months)까지 1씩 감소
            # (수정: start_tick보다 예측 수명이 크면 start_tick에서 시작, 아니면 예측수명+10 에서 시작)
            if predicted_months > start_tick:
                start_point = start_tick
            else:
                start_point = max(predicted_months + 10, predicted_months) # 최소 10번은 돌도록
            
            for i in range(start_point, predicted_months - 1, -1):
                result_placeholder.markdown(
                    f"<div class=\"result-text\">{i}</div>", 
                    unsafe_allow_html=True
                )
                time.sleep(0.05) # 0.05초 간격

            # 4. 카운트다운 완료 후 최종 결과 메시지 고정
            result_placeholder.markdown(
                f"<div class=\"result-text\">{result_message}</div>", 
                unsafe_allow_html=True
            )
            
            # 디펜스 논리 설명
            st.markdown(f'<p class="sub-text" style="color: #AAA;">{status_text}</p>', unsafe_allow_html=True)
            st.markdown(f"""
                <p style='font-size: 16px; color: #E0E0E0;'>
                이 예측은 <b>'{text}'</b>의 실시간 최대 상승 기울기 (<b>{realtime_slope:.2f}</b>)를 기반으로,
                훈련 데이터셋에서 가장 유사한 기울기를 가진 단어들
                (예: <b>{', '.join(nearby_words_list)}</b>)의 평균 수명을 계산한 결과입니다.
                </p>
            """, unsafe_allow_html=True)


        except Exception as e:
            if "429" in str(e):
                st.error("❌ Google Trends 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
            else:
                st.error(f"❌ 실시간 분석 중 오류 발생: {e}")
        
        # 세션 상태 초기화
        del st.session_state.text

if __name__ == "__main__":
    main()

st.markdown("""
<div class="fog-container">
  <div class="fog-img fog-img-first"></div>
  <div class="fog-img fog-img-second"></div>
</div>
""", unsafe_allow_html=True)
