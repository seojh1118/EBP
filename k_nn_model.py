import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler # 👈 [필수] 스케일러 임포트
import joblib # 👈 [필수] 모델/스케일러 저장용

# 1. 데이터 로드 (1단계에서 생성된 CSV)
try:
    df = pd.read_csv('final_training_dataset.csv') 
except FileNotFoundError:
    print("ERROR: final_training_dataset.csv 파일을 찾을 수 없습니다.")
    print("1단계: lifetime_calculator.py를 먼저 실행하여 최종 데이터셋을 저장해주세요.")
    exit()

# 2. 데이터 전처리 및 X, Y 분리
df_train = df[df['Lifetime (Months)'] != 'Ongoing'].copy()

# [중요] 훈련 전 결측치 처리 (app.py와 동일하게)
df_train['Max_Rising_Slope'] = df_train['Max_Rising_Slope'].fillna(0)
df_train['Peak_Value'] = df_train['Peak_Value'].fillna(0) # 👈 [신규] Peak_Value 처리

# Y축: 수명 (숫자형으로 변환)
Y = df_train['Lifetime (Months)'].astype(int)

# X축: 입력 피쳐 (3개 사용)
features = ['Word_Length', 'Max_Rising_Slope', 'Peak_Value']
X = df_train[features]

print("--- 훈련에 사용될 피처 (X) ---")
print(X.head())
print("\n--- 훈련에 사용될 타겟 (Y) ---")
print(Y.head())

# 3. 모델 훈련 및 테스트 데이터 분할
X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.3, random_state=42)

# 4.피처 스케일링 (KNN에 필수)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"\n데이터 스케일링 완료")

# 5. k-NN 모델 훈련 (k=3으로 설정)
k = 3
# 'distance' 가중치 (가까운 이웃에 더 큰 영향력)를 사용하면 성능이 향상될 수 있음
knn_model = KNeighborsRegressor(n_neighbors=k, weights='distance') 
knn_model.fit(X_train_scaled, Y_train) # 스케일된 데이터로 훈련

# 6. 모델 평가
score = knn_model.score(X_test_scaled, Y_test) # 스케일된 데이터로 평가
print(f"\n--- 모델 훈련 완료 (k={k}) ---")
print(f"✅ 모델 평가 점수 (R^2): {score:.4f}")

# 7. 훈련된 모델과 '스케일러'를 파일로 저장
joblib.dump(knn_model, 'knn_model.pkl')
joblib.dump(scaler, 'scaler.pkl')

print("✅ 'knn_model.pkl' (모델) 파일 저장 성공.")
print("✅ 'scaler.pkl' (3-feature 스케일러) 파일 저장 성공.")
