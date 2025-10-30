import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsRegressor # k-NN 회귀 모델 임포트
from sklearn.model_selection import train_test_split # 데이터 분할 도구

# 1. 데이터 로드
# (주의: 이 부분은 실제로 lifetime_calculator.py에서 최종 출력된 데이터를 CSV로 저장했다고 가정)
try:
    df = pd.read_csv('final_training_dataset.csv') 
    # 만약 CSV가 없다면, lifetime_calculator.py를 실행하여 final_dataset.csv를 먼저 생성해야 합니다.
except FileNotFoundError:
    print("ERROR: final_training_dataset.csv 파일을 찾을 수 없습니다. lifetime_calculator.py를 먼저 실행하여 최종 데이터셋을 저장해주세요.")
    exit()

# 2. 데이터 전처리 및 X, Y 분리

# 'Ongoing'은 예측 목표(Y)가 될 수 없으므로 제외 (미팅 후 처리 방식 확정)
df_train = df[df['Lifetime (Months)'] != 'Ongoing'].copy()

# Y축: 수명 (숫자형으로 변환)
Y = df_train['Lifetime (Months)'].astype(int)

# X축: 입력 피쳐 (단어 길이만 사용 - KoNLPy 오류 임시 회피)
X = df_train[['Word_Length']]

# 3. 모델 훈련 및 테스트 데이터 분할
X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.3, random_state=42)

# 4. k-NN 모델 훈련 (k=3으로 설정)
k = 3
knn_model = KNeighborsRegressor(n_neighbors=k)
knn_model.fit(X_train, Y_train)

# 5. 모델 성능 평가 (미팅 자료에 포함)
score = knn_model.score(X_test, Y_test)
print(f"--- k-NN 모델 훈련 완료 (k={k}) ---")
print(f"테스트 데이터셋 정확도 (R-squared): {score:.2f}")

# 6. 새로운 단어 예측 시뮬레이션

# '아바타'라는 신조어가 입력되었다고 가정 (단어 길이 3)
new_word_length = 3 

# 예측
predicted_lifetime = knn_model.predict([[new_word_length]])

# 예측 결과를 가장 가까운 정수로 변환
predicted_months = int(np.round(predicted_lifetime[0]))

print(f"\n--- 새로운 단어 예측 시뮬레이션 ---")
print(f"입력 단어 길이: {new_word_length}")
print(f"예측된 수명: {predicted_months} 개월")

# (이후 Streamlit app.py에 이 예측 로직을 통합해야 합니다)