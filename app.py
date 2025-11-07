import streamlit as st
import speech_recognition as sr
import pandas as pd
import numpy as np
from pytrends.request import TrendReq
import datetime
import time
import random  
import joblib  # 모델/스케일러 로드용
from sklearn.metrics.pairwise import euclidean_distances  # '유사 단어' 계산용

# --- 0. [수정] 3-Feature 모델 및 데이터 로드 ---
@st.cache_resource
def load_assets():
    """
    3개 피처로 미리 훈련된 모델(.pkl), 스케일러(.pkl),
    그리고 DB 및 유사 단어 비교에 사용할 CSV 파일을 로드합니다.
    """
    try:
        # 1. 3-feature로 훈련된 파일 로드
        knn_model = joblib.load('knn_model.pkl')
        scaler = joblib.load('scaler.pkl')
        
        # 2. 3-feature가 포함된 CSV 로드
        df = pd.read_csv('final_training_dataset.csv')
        df_train = df[df['Lifetime (Months)'] != 'Ongoing'].copy()
        
        # 3. [핵심 수정] 모델이 학습한 피처 3개 (순서 일치 필수)
        features = ['Word_Length', 'Max_Rising_Slope', 'Peak_Value']
        
        # [중요] NaN 값 처리 (훈련 시와 동일)
        df_train['Max_Rising_Slope'] = df_train['Max_Rising_Slope'].fillna(0)
        df_train['Peak_Value'] = df_train['Peak_Value'].fillna(0) # Peak_Value 처리
        
        # 4. '유사 단어' 비교를 위해 스케일링된 훈련 데이터 X를 미리 준비
        # (scaler는 3개 피처로 훈련되어 있어야 함)
        X_train_scaled = scaler.transform(df_train[features])
        
        # 5. 유사 단어의 '이름' 목록
        Word_names = df_train['Word'].values
        
        # 6. 모든 자산 반환 (features 리스트도 함께 반환)
        return df_train, knn_model, scaler, X_train_scaled, Word_names, features
    
    except FileNotFoundError:
        st.error("❌ ERROR: 'knn_model.pkl', 'scaler.pkl' 또는 'final_training_dataset.csv' 파일을 찾을 수 없습니다.")
        st.info("선행 단계: 3-feature로 lifetime_calculator.py와 k_nn_model.py를 먼저 실행하세요.")
        return None, None, None, None, None, None
    except Exception as e:
        st.error(f"❌ ERROR: 모델 로드 중 오류 발생: {e}")
        st.error("🚨 훈련(k_nn_model.py)과 앱(app.py)의 피처 개수(3개)가 일치하는지 확인하세요.")
        return None, None, None, None, None, None

# --- 1. 3-Feature 실시간 계산 함수 ---
def get_realtime_features_harmonized(word):
    try:
        pytrends = TrendReq(hl='ko-KR', tz=540)
        time.sleep(1 + random.uniform(0, 2))
        pytrends.build_payload([word], cat=0, timeframe='all', geo='KR')
        interest_df = pytrends.interest_over_time()
        if interest_df.empty or word not in interest_df.columns:
            st.warning(f"'{word}'에 대한 (전체 기간) 트렌드 데이터가 충분하지 않습니다.")
            return None, None
        series = interest_df[word]
        # --- 피처 3: Peak_Value ---
        peak_value = series.max()
        
        if peak_value == 0:
            max_rising_slope = 0.0
        else:
            # --- 피처 2: Max_Rising_Slope  ---
            peak_date_index = series.idxmax()
            start_threshold = peak_value * 0.1 
            start_index = series[series >= start_threshold].first_valid_index()
            
            max_rising_slope = 0.0
            if start_index is not None and start_index < peak_date_index:
                rising_period = series.loc[start_index:peak_date_index]
                if len(rising_period) > 1:
                    max_slope = rising_period.diff().max()
                    if not pd.isna(max_slope):
                        max_rising_slope = max_slope
            max_rising_slope = max(0.0, max_rising_slope)

        # --- 피처 1: Word_Length ---
        word_len = len(word.replace(" ", ""))

        # 핵심 수정] 3개 피처 반환 (훈련 순서와 동일: [길이, 기울기, 최대값])
        final_features = [word_len, max_rising_slope, peak_value]
        
        return final_features, series

    except Exception as e:
        if "429" in str(e):
            st.error("❌ 실시간 분석 API 요청 한도를 초과했습니다 (429 Error). 1분 후 다시 시도해주세요.")
        else:
            st.error(f"트렌드 데이터 수집 중 오류: {e}")
        return None, None


# --- 2. [V1] 음성 인식 콜백 함수 (STT) (변경 없음) ---
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
        except sr.RequestError as e:
            st.error(f"❌ Google STT 서비스 오류: {e}")
        except Exception as e:
            st.error(f"❌ STT 처리 중 알 수 없는 오류: {e}")

# --- 3. CSS 로드 함수 (변경 없음) ---
def load_css(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"❌ ERROR: 'style.css' 파일을 찾을 수 없습니다.")

# --- 4. 메인 실행 함수 (3-Feature 반영) ---
def main():
    load_css("style.css")
    
    try:
        st.video("img/smoke.mp4", start_time=0)
    except Exception as e:
        st.warning(f"비디오 파일을 불러올 수 없습니다: {e}")

    
    st.markdown('<h1 class="title-text"><span>☯︎단어 멸망 시계☯︎</span></h1>', unsafe_allow_html=True)
    st.markdown("<p>음성으로 신조어를 입력하면, 3가지 '유행 패턴'을 실시간 분석하여 수명을 예측합니다.</p>", unsafe_allow_html=True)

    # 1. 3-Feature 자산 로드
    assets = load_assets()
    # features_list 추가
    df_train, knn_model, scaler, X_train_scaled, Word_names, features_list = assets
    
    if knn_model is None:
        return 

    # 2. STT 버튼
    st.button("Click to Speak", on_click=on_stt_button_click, use_container_width=True)

    # 3.  3-Feature STT 완료 후 로직
    if "text" in st.session_state and st.session_state.text:
        text = st.session_state.text
        st.markdown(f"<p class='user-input'>입력된 단어: \"{text}\"</p>", unsafe_allow_html=True)

        live_features = None 
        live_series = None   
        is_new_word = False
        
        try:
            # --- (A) 하이브리드 로직: DB(CSV) 우선 검색 ---
            word_data_from_db = df_train[df_train['Word'] == text]
            
            if not word_data_from_db.empty:
                st.info("💡 학습된 단어입니다. 저장된 데이터로 분석합니다.")
                #  3개 피처(features_list)를 DB에서 로드
                live_features = word_data_from_db[features_list].values.tolist()[0]
                is_new_word = False
                
            else:
                # [경로 2: DB에 단어가 없음 (신조어)]
                with st.spinner(f"신조어 '{text}'의 '유행 패턴'을 실시간 분석 중..."):
                    #  3개 피처를 실시간 계산
                    live_features, live_series = get_realtime_features_harmonized(text) 
                is_new_word = True

            if live_features is None:
                st.error("데이터를 분석할 수 없습니다.")
                del st.session_state.text 
                st.stop() 
            
            # --- (B) 3-Feature 스케일링 및 예측 ---
            # 3개 피처 언패킹
            word_len_feature, max_rising_slope, peak_value = live_features
            
            # 2. 3-Feature 스케일링 (훈련된 scaler 사용)
            X_live_scaled = scaler.transform(np.array([live_features]))

            # 3. 3-Feature 모델 예측
            predicted_lifetime = knn_model.predict(X_live_scaled)
            predicted_months = int(np.round(predicted_lifetime[0]))
            
            # 4. '유사 단어' 찾기 (3차원 공간에서)
            K = 5
            distances = euclidean_distances(X_live_scaled, X_train_scaled).flatten()
            
            if is_new_word:
                nearest_indices = np.argsort(distances)[:K]
            else:
                nearest_indices = np.argsort(distances)[1:K+1]
                
            nearby_words_list = Word_names[nearest_indices]

            # --- (C) 결과 표시 및 카운트다운 ---
            st.success(f"✅ '{text}'의 '유행 패턴' 분석 완료!")
            #  3개 피처 표시
            st.markdown(f"> (단어 길이: **{word_len_feature}**, 최대 기울기: **{max_rising_slope:.2f}**, 최대 관심도: **{peak_value:.2f}**)")
            
            # [V2 기능] 실시간 차트 표시
            if is_new_word and live_series is not None:
                st.info(f"'{text}'의 전체 기간 트렌드 (Google Trends, KR)")
                st.line_chart(live_series)

            st.subheader('🕰️ 예측된 멸망까지 남은 시간')
            
            # 결과 메시지 설정
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

            # 카운트다운 로직
            result_placeholder = st.empty()
            start_tick = 60 
            if predicted_months > start_tick:
                start_point = start_tick
            else:
                start_point = max(predicted_months + 10, predicted_months)
            
            for i in range(start_point, predicted_months - 1, -1):
                result_placeholder.markdown(f"<div class=\"result-text\">{i}</div>", unsafe_allow_html=True)
                time.sleep(0.05) 

            # 최종 결과 고정
            result_placeholder.markdown(f"<div class=\"result-text\">{result_message}</div>", unsafe_allow_html=True)
            
            # 3-Feature 디펜스 논리
            st.markdown(f'<p class="sub-text" style="color: #AAA;">{status_text}</p>', unsafe_allow_html=True)
            st.markdown(f"""
                <p style='font-size: 16px; color: #E0E0E0;'>
                (예측 근거: <b>'{text}'</b>의 3가지 패턴
                (길이 {word_len_feature}, 기울기 {max_rising_slope:.2f}, 최대관심도 {peak_value:.2f})을
                기존 단어 (<b>{', '.join(nearby_words_list)}</b> 등)의 
                유사 패턴과 비교하여 수명을 예측)
                </p>
            """, unsafe_allow_html=True)


        except Exception as e:
            if "429" in str(e):
                st.error("❌ Google Trends 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
            else:
                st.error(f"❌ 실시간 분석 중 오류 발생: {e}")
                import traceback
                st.error(traceback.format_exc()) 
        
        del st.session_state.text

if __name__ == "__main__":
    st.set_page_config(page_title="단어 멸망 시계", layout="centered") 
    main()

#  안개 효과 CSS
st.markdown("""
<div class="fog-container">
  <div class="fog-img fog-img-first"></div>
  <div class="fog-img fog-img-second"></div>
</div>
""", unsafe_allow_html=True)
