import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
import numpy as np
import joblib

# 1. 4-Feature 데이터셋 로드
try:
    df = pd.read_csv('final_training_dataset.csv', index_col='Word')
except FileNotFoundError:
    print("❌ ERROR: 'final_training_dataset.csv' 파일을 찾을 수 없습니다.")
    print("먼저 lifetime_calculator.py를 실행하세요.")
    exit()

# 2. 훈련 데이터 준비 (Ongoing 제외)
df_train = df[df['Lifetime (Months)'] != 'Ongoing'].copy()
df_train['Lifetime (Months)'] = df_train['Lifetime (Months)'].astype(int)

# 3. [수정] 4가지 피처를 X, 수명을 Y로 설정
features = ['Word_Length', 'Max_Rising_Slope', 'Initial_Volatility', 'Initial_Decay_Rate']
X = df_train[features]
Y = df_train['Lifetime (Months)']

# 결측치(NaN)가 있을 경우 0으로 대체 (안정성)
X = X.fillna(0)

# 4. 데이터 분할
X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

# 5. [수정] 피처 스케일링 (StandardScaler 사용)
# k-NN은 거 기반 모델이므로 스케일링이 중요함
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 6. k-NN 모델 훈련
k = 3 # 이웃 수
knn_model = KNeighborsRegressor(n_neighbors=k)
knn_model.fit(X_train_scaled, Y_train)

# 7. 모델 평가
Y_pred = knn_model.predict(X_test_scaled)
rmse = np.sqrt(mean_squared_error(Y_test, Y_pred))
print(f"\n--- 4-Feature k-NN (k={k}) 모델 성능 ---")
print(f"테스트 데이터 RMSE: {rmse:.2f} 개월")
print(f"테스트 데이터 R-squared: {knn_model.score(X_test_scaled, Y_test):.4f}")

# 8. [중요] 훈련된 모델과 스케일러 저장
joblib.dump(knn_model, 'knn_model.pkl')
joblib.dump(scaler, 'scaler.pkl')

print("\n✅ 'knn_model.pkl' (모델) 및 'scaler.pkl' (스케일러) 저장 완료.")


