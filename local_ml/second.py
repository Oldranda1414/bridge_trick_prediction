import os
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error
from scikeras.wrappers import KerasRegressor
from tensorflow import keras
from tensorflow.keras import layers, callbacks

# === Import your loader ===
from load_dataset import load_csv_to_dataset

# === Load dataset ===
X, y = load_csv_to_dataset("bridge_data.csv")
print("Dataset loaded:", X.shape, y.shape)

# === Split ===
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# === Define model builder ===
def build_model(
    n_hidden1=256,
    n_hidden2=128,
    n_hidden3=64,
    dropout_rate=0.3,
    learning_rate=1e-3
):
    model = keras.Sequential([
        layers.Input(shape=(X.shape[1],)),
        layers.Dense(n_hidden1, activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(dropout_rate),
        layers.Dense(n_hidden2, activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(dropout_rate / 2),
        layers.Dense(n_hidden3, activation='relu'),
        layers.Dense(1, activation='linear')
    ])
    opt = keras.optimizers.Adam(learning_rate=learning_rate)
    model.compile(optimizer=opt, loss='mse', metrics=['mae'])
    return model

# === Wrap for sklearn ===
regressor = KerasRegressor(model=build_model, verbose=0, epochs=50)

# === Define grid of hyperparameters ===
param_grid = {
    "model__n_hidden1": [128, 256],
    "model__n_hidden2": [64, 128],
    "model__dropout_rate": [0.2, 0.3, 0.4],
    "model__learning_rate": [1e-3, 5e-4],
    "batch_size": [64, 128],
    "epochs": [50, 80]
}

# === Define callbacks ===
early_stopping = callbacks.EarlyStopping(
    monitor='val_loss',
    patience=5,
    restore_best_weights=True
)

# === Grid search ===
grid = GridSearchCV(
    estimator=regressor,
    param_grid=param_grid,
    scoring="neg_mean_absolute_error",
    cv=3,
    verbose=2,
    n_jobs=-1,
)

grid_result = grid.fit(
    X_train, y_train,
    validation_split=0.2,
    callbacks=[early_stopping]
)

# === Best params ===
print("\nBest parameters found:")
print(grid_result.best_params_)
print(f"Best CV MAE: {-grid_result.best_score_:.4f}")

# === Evaluate on test set ===
best_model = grid_result.best_estimator_.model_
y_pred = best_model.predict(X_test).flatten()
test_mae = mean_absolute_error(y_test, y_pred)
print(f"Test MAE: {test_mae:.4f} tricks")

# === Save training curves for the best model ===
os.makedirs("plots", exist_ok=True)
history = grid_result.best_estimator_.model_.history_

plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Val Loss')
plt.title('Training vs Validation Loss')
plt.xlabel('Epochs')
plt.ylabel('MSE Loss')
plt.legend()
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(history.history['mae'], label='Train MAE')
plt.plot(history.history['val_mae'], label='Val MAE')
plt.title('Training vs Validation MAE')
plt.xlabel('Epochs')
plt.ylabel('MAE')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig("plots/best_model_training_curves.png", dpi=300)
plt.close()

print("✅ Training curves saved to: plots/best_model_training_curves.png")
