# bridge_trump_baseline.py
import os
import hashlib
import numpy as np
import pandas as pd
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split, GroupKFold
# import matplotlib.pyplot as plt

from load_dataset import load_csv_to_dataset

# === Load dataset ===
X, y = load_csv_to_dataset("bridge_data.csv")
print("Dataset loaded:", X.shape, y.shape)

# === Train/test split ===
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# === Build model ===
def build_model(input_dim):
    model = keras.Sequential([
        layers.Input(shape=(input_dim,)),
        layers.Dense(256, activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(0.3),
        layers.Dense(128, activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(0.2),
        layers.Dense(64, activation='relu'),
        layers.Dense(1, activation='linear'),
    ])
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss='mse', metrics=['mae'])
    return model

def compute_deal_id_series(df):
    # Concatenate the 4 hands in a normalized manner to detect identical deals.
    s = (df['south_hand'].fillna('') + '|' +
         df['west_hand'].fillna('') + '|' +
         df['north_hand'].fillna('') + '|' +
         df['east_hand'].fillna(''))
    return s.apply(lambda x: hashlib.md5(x.encode('utf-8')).hexdigest())

def group_kfold_cv(df, X, y, k=5, epochs=50, batch_size=128):
    groups = compute_deal_id_series(df)
    gkf = GroupKFold(n_splits=k)
    fold_maes = []
    for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups)):
        print(f"\n=== Group Fold {fold_idx+1}/{k} ===")
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = build_model(X.shape[1])
        early = keras.callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early],
            verbose=1
        )
        loss, mae = model.evaluate(X_val, y_val, verbose=0)
        print(f"Group Fold {fold_idx+1} MAE: {mae:.4f}")
        fold_maes.append(mae)

    mean_mae = np.mean(fold_maes)
    std_mae = np.std(fold_maes, ddof=1)
    ci95 = 1.96 * std_mae / np.sqrt(k)
    print(f"\nGroupKFold MAE: mean={mean_mae:.4f}, std={std_mae:.4f}, 95% CI ±{ci95:.4f}")
    return fold_maes


if __name__ == "__main__":
    df = pd.read_csv("bridge_data.csv")
    X, y = load_csv_to_dataset("bridge_data.csv")
    print("X shape", X.shape)

    # run GroupKFold
    fold_maes_group = group_kfold_cv(df, X, y, k=5, epochs=50, batch_size=128)

# # === Add early stopping ===
# early_stopping = keras.callbacks.EarlyStopping(
#     monitor='val_loss',
#     patience=5,
#     restore_best_weights=True
# )
#
# # === Train model ===
# history = model.fit(
#     X_train, y_train,
#     validation_data=(X_test, y_test),
#     epochs=50,
#     batch_size=128,
#     callbacks=[early_stopping],
#     verbose=1
# )
#
# # === Evaluate performance ===
# loss, mae = model.evaluate(X_test, y_test)
# print(f"Test MAE: {mae:.4f}")

# === Save plots ===
# os.makedirs("plots", exist_ok=True)
#
# plt.figure(figsize=(12, 5))
#
# # Loss curve
# plt.subplot(1, 2, 1)
# plt.plot(history.history['loss'], label='Train Loss')
# plt.plot(history.history['val_loss'], label='Val Loss')
# plt.title('Training vs Validation Loss')
# plt.xlabel('Epochs')
# plt.ylabel('MSE Loss')
# plt.legend()
# plt.grid(True)
#
# # MAE curve
# plt.subplot(1, 2, 2)
# plt.plot(history.history['mae'], label='Train MAE')
# plt.plot(history.history['val_mae'], label='Val MAE')
# plt.title('Training vs Validation MAE')
# plt.xlabel('Epochs')
# plt.ylabel('Mean Absolute Error')
# plt.legend()
# plt.grid(True)
#
# plt.tight_layout()
# plt.savefig("plots/training_curves.png", dpi=300)
# plt.close()
#
# print("✅ Training curves saved to: plots/training_curves.png")
#
