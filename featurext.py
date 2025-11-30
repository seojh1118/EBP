import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

def calculate_advanced_features(series, word_text):
    """
    [개선된 로직]
    훈련(lifetime_calculator)과 서빙(app)에서 공통으로 사용할 함수.
    
    Returns:
        dict: {'Word_Length', 'Max_Rising_Slope', 'Initial_Volatility', 'Initial_Decay_Rate', 'Lifetime'}
    """
    # 1. 노이즈 완화 (Smoothing)
    smooth_series = series.rolling(window=3, min_periods=1).mean()
    
    # 2. Peak 지점 찾기
    peak_idx = smooth_series.idxmax()
    peak_value = smooth_series.max()
    
    # 검색량이 너무 적으면 분석 불가 (Threshold 5)
    if peak_value < 5:
        return None

    # index가 날짜형이 아닐 경우를 대비해 정수형 인덱스 생성
    y_values = smooth_series.values
    x_values = np.arange(len(y_values))
    peak_loc_int = smooth_series.index.get_loc(peak_idx)

    # ---------------------------------------------------------
    # [수정 요청 1] Initial_Decay_Rate: Peak 이후 Slope 기반 + Smoothing
    # ---------------------------------------------------------
    # Peak 이후 데이터가 충분한지 확인 (최소 3개 포인트)
    if peak_loc_int + 3 < len(y_values):
        # Peak 직후 3~6개월(혹은 주) 구간을 잘라냄
        decay_window_end = min(peak_loc_int + 6, len(y_values))
        y_decay = y_values[peak_loc_int : decay_window_end]
        x_decay = x_values[peak_loc_int : decay_window_end].reshape(-1, 1)
        
        # 선형 회귀로 기울기 계산 (음수일수록 급격한 하락)
        if len(y_decay) > 1:
            reg = LinearRegression().fit(x_decay, y_decay)
            decay_slope = reg.coef_[0]
            # 기울기는 보통 음수이므로, '감소율'의 크기를 보기 위해 부호 반전 or 절댓값
            # 양수로 변환하되, 상승해버리는 경우는 0 처리
            initial_decay_rate = -decay_slope if decay_slope < 0 else 0
        else:
            initial_decay_rate = 0
    else:
        initial_decay_rate = 0

    # ---------------------------------------------------------
    # [수정 요청 2] Lifetime: 1% 이하로 30일(약 4주/1개월) 이상 지속
    # ---------------------------------------------------------
    # 구글 트렌드 데이터 간격(Monthly/Weekly)에 따라 '30일'의 의미가 달라짐.
    # 여기서는 데이터 포인트 1~2개가 연속으로 Threshold 밑일 때를 사망으로 간주.
    
    threshold = peak_value * 0.01  # 1% 기준
    lifetime_months = "Ongoing"
    
    # Peak 이후부터 탐색
    for i in range(peak_loc_int + 1, len(y_values) - 1):
        # 현재 시점과 다음 시점이 모두 Threshold 이하라면 '사망'으로 판정 (안정성 확보)
        if y_values[i] < threshold and y_values[i+1] < threshold:
            # 수명 = (사망 시점 - 시작 시점) or (사망 시점 - Peak 시점)
            # 여기서는 '총 수명' 관점이므로 (사망 시점 - 데이터 시작점)으로 계산하거나
            # 단순히 Peak 이후 경과 시간을 쓸 수도 있음. 
            # 기존 코드 맥락상 '인덱스 거리'를 수명으로 봅니다.
            
            # (옵션) 시작점(Rising point)을 찾아 거기서부터 잴 수도 있음. 
            # 여기서는 단순화하여 Peak까지 도달 시간 + Peak 이후 생존 시간 합산
            lifetime_months = i 
            break
            
    # ---------------------------------------------------------
    # 기존 피처 유지 (Word Length, Max_Rising_Slope, Volatility)
    # ---------------------------------------------------------
    # 3. Word Length
    word_len = len(word_text)
    
    # 4. Max Rising Slope (Peak 이전 최대 기울기)
    max_rising_slope = 0
    if peak_loc_int > 0:
        # Peak 이전 구간에 대해 차분(diff) 계산
        pre_peak = smooth_series.iloc[:peak_loc_int+1]
        diffs = pre_peak.diff()
        if not diffs.empty:
            max_rising_slope = diffs.max()
            
    # 5. Initial Volatility (초기 변동성) - Peak 이전 표준편차
    if peak_loc_int > 1:
        initial_volatility = smooth_series.iloc[:peak_loc_int].std()
    else:
        initial_volatility = 0
        
    # NaN 방지
    max_rising_slope = 0 if pd.isna(max_rising_slope) else max_rising_slope
    initial_volatility = 0 if pd.isna(initial_volatility) else initial_volatility

    return {
        'Word': word_text,
        'Word_Length': word_len,
        'Max_Rising_Slope': max_rising_slope,
        'Initial_Volatility': initial_volatility,
        'Initial_Decay_Rate': initial_decay_rate, # 수정된 로직 반영
        'Lifetime (Months)': lifetime_months      # 수정된 로직 반영
    }




