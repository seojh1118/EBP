import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
import numpy as np
import joblib

try:
    df = pd.read_csv('final_training_dataset.csv', index_col='Word')
except FileNotFoundError:
    print("❌ ERROR: 'final_training_dataset.csv' 파일을 찾을 수 없습니다.")
    print("먼저 lifetime_calculator.py를 실행하세요.")
    exit()

df_train = df[df['Lifetime (Months)'] != 'Ongoing'].copy()
df_train['Lifetime (Months)'] = df_train['Lifetime (Months)'].astype(int)

features = ['Word_Length', 'Max_Rising_Slope', 'Initial_Volatility', 'Initial_Decay_Rate']
X = df_train[features]
Y = df_train['Lifetime (Months)']

X = X.fillna(0)

X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

k = 3 # 이웃 수
knn_model = KNeighborsRegressor(n_neighbors=k)
knn_model.fit(X_train_scaled, Y_train)

Y_pred = knn_model.predict(X_test_scaled)
rmse = np.sqrt(mean_squared_error(Y_test, Y_pred))
print(f"\n--- 4-Feature k-NN (k={k}) 모델 성능 ---")
print(f"테스트 데이터 RMSE: {rmse:.2f} 개월")
print(f"테스트 데이터 R-squared: {knn_model.score(X_test_scaled, Y_test):.4f}")

joblib.dump(knn_model, 'knn_model.pkl')
joblib.dump(scaler, 'scaler.pkl')

print("\n✅ 'knn_model.pkl' (모델) 및 'scaler.pkl' (스케일러) 저장 완료.")



