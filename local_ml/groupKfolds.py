import os
import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import GroupKFold

from load_dataset import load_csv_to_dataset

# === Load dataset ===
X, y = load_csv_to_dataset("bridge_data.csv")
print("Dataset loaded:", X.shape, y.shape)

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
    os.makedirs("plots", exist_ok=True)
    groups = compute_deal_id_series(df)
    gkf = GroupKFold(n_splits=k)

    fold_maes = []
    all_val_losses = []

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

        # Record validation loss per epoch
        all_val_losses.append(history.history['val_loss'])

        loss, mae = model.evaluate(X_val, y_val, verbose=0)
        print(f"Group Fold {fold_idx+1} MAE: {mae:.4f}")
        fold_maes.append(mae)

    # === Compute statistics ===
    mean_mae = np.mean(fold_maes)
    std_mae = np.std(fold_maes, ddof=1)
    ci95 = 1.96 * std_mae / np.sqrt(k)
    print(f"\nGroupKFold MAE: mean={mean_mae:.4f}, std={std_mae:.4f}, 95% CI ±{ci95:.4f}")

    # === Plot 1: MAE per fold ===
    plt.figure(figsize=(8, 5))
    plt.bar(range(1, k + 1), fold_maes, color="#4CAF50", alpha=0.8)
    plt.axhline(mean_mae, color="black", linestyle="--", label=f"Mean MAE = {mean_mae:.3f}")
    plt.fill_between(
        [0, k + 1],
        mean_mae - ci95,
        mean_mae + ci95,
        color="gray",
        alpha=0.2,
        label="95% CI"
    )
    plt.title("GroupKFold MAE per Fold", fontsize=14)
    plt.xlabel("Fold")
    plt.ylabel("Mean Absolute Error")
    plt.legend()
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig("plots/groupkfold_mae_per_fold.png", dpi=300)
    plt.close()

    # === Plot 2: Mean validation loss curve ===
    min_len = min(len(v) for v in all_val_losses)
    val_curves = [v[:min_len] for v in all_val_losses]
    mean_curve = np.mean(val_curves, axis=0)
    std_curve = np.std(val_curves, axis=0)

    plt.figure(figsize=(8, 5))
    epochs_range = np.arange(1, min_len + 1)
    plt.plot(epochs_range, mean_curve, label="Mean Val Loss", color="#2196F3")
    plt.fill_between(epochs_range, mean_curve - std_curve, mean_curve + std_curve,
                     color="#2196F3", alpha=0.2, label="±1 std")
    plt.title("Validation Loss across Folds", fontsize=14)
    plt.xlabel("Epochs")
    plt.ylabel("MSE Loss")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig("plots/groupkfold_val_loss.png", dpi=300)
    plt.close()

    print("\n✅ Saved plots:")
    print("   - plots/groupkfold_mae_per_fold.png")
    print("   - plots/groupkfold_val_loss.png")

    return fold_maes


# === Main ===
if __name__ == "__main__":
    df = pd.read_csv("bridge_data.csv")
    X, y = load_csv_to_dataset("bridge_data.csv")
    print("X shape", X.shape)
    fold_maes_group = group_kfold_cv(df, X, y, k=5, epochs=50, batch_size=128)

