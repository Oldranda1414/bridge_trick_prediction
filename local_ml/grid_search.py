from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import GridSearchCV, train_test_split
from scikeras.wrappers import KerasRegressor
from load_dataset import load_csv_to_dataset

# === Load dataset ===
X, y = load_csv_to_dataset("bridge_data.csv")
print("Dataset loaded:", X.shape, y.shape)

# === Build model function for KerasRegressor ===
def build_model(n_layers=2, n_neurons=128, dropout=0.2, lr=1e-3):
    model = keras.Sequential()
    model.add(layers.Input(shape=(X.shape[1],)))
    
    for _ in range(n_layers):
        model.add(layers.Dense(n_neurons, activation='relu'))
        model.add(layers.Dropout(dropout))
        model.add(layers.BatchNormalization())
    
    model.add(layers.Dense(1, activation='linear'))
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=lr),
                  loss='mse', metrics=['mae'])
    return model


# === Wrap Keras model for scikit-learn ===
regressor = KerasRegressor(
    model=build_model,
    model__n_layers=2,
    model__n_neurons=128,
    model__dropout=0.2,
    model__lr=1e-3,
    verbose=0
)

# === Define grid of hyperparameters ===
param_grid = {
    'model__n_layers': [2, 3],
    'model__n_neurons': [64, 128, 256],
    'model__dropout': [0.1, 0.2, 0.3],
    'model__lr': [1e-3, 5e-4],
    'batch_size': [64, 128],
    'epochs': [30]
}

# === Split dataset for GridSearchCV evaluation ===
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# === Run grid search ===
grid = GridSearchCV(estimator=regressor, param_grid=param_grid,
                    scoring='neg_mean_absolute_error', cv=3, n_jobs=-1, verbose=2)

grid_result = grid.fit(X_train, y_train)

# === Print results ===
print("Best MAE: %.4f using %s" % (-grid_result.best_score_, grid_result.best_params_))

means = -grid_result.cv_results_['mean_test_score']
stds = grid_result.cv_results_['std_test_score']
params = grid_result.cv_results_['params']

# === Optional: Plot results ===
import matplotlib.pyplot as plt

plt.figure(figsize=(10,6))
plt.errorbar(range(len(means)), means, yerr=stds, fmt='o')
plt.xticks(range(len(means)), [str(p) for p in params], rotation=90)
plt.ylabel('MAE')
plt.title('Grid Search Results')
plt.tight_layout()
plt.savefig("grid_search_results.png", dpi=300)
plt.close()
print("✅ Saved plot: grid_search_results.png")

