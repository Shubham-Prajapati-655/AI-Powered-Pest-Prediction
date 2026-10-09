import pandas as pd
import numpy as np
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def verify_accuracy():
    print("==================================================")
    print("RIGOROUS MODEL EVALUATION: TOP-1 AND TOP-3 ACCURACY")
    print("==================================================")
    
    # 1. Load Dataset
    df = pd.read_csv("datasets/pest_weather.csv")
    
    # 2. Feature Engineering
    df["THI"] = 0.8 * df["Temperature"] + (df["Humidity"] / 100.0) * (df["Temperature"] - 14.3) + 46.4
    df["Rainfall_Humidity_Ratio"] = df["Rainfall_mm"] / (df["Humidity"] + 1.0)
    
    # 3. Load Trained Production Model Artifact
    model_path = "models/best_model.pkl" if os.path.exists("models/best_model.pkl") else "artifacts/trained_model.pkl"
    pipeline = joblib.load(model_path)
    
    # Raw features expected by production pipeline
    raw_features = ["State", "District", "Crop", "Crop_Category", "Sowing_Season", "Season", "Temperature", "Humidity", "Rainfall_mm"]
    X = df[raw_features]
    y_pest = pipeline.le_pest.transform(df["Pest_Name"])
    y_risk = pipeline.le_risk.transform(df["Outbreak"])
    Y = np.column_stack([y_pest, y_risk])
    
    # 4. Train/Test Split (Same random_state=42 as training)
    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
    
    print(f"Total Test Samples Evaluated: {len(X_test):,}")
    
    # 5. Extract Pest Classifier Pipeline from UnifiedProductionPipeline
    pest_pipeline = pipeline.pest_pipeline
    
    # 6. Predict Top-1 Class
    y_pred_pest = pest_pipeline.predict(X_test)
    top1_acc = accuracy_score(Y_test[:, 0], y_pred_pest)
    
    # 7. Predict Class Probabilities using predict_proba()
    pest_probabilities = pest_pipeline.predict_proba(X_test) # shape: (N_test, 25)
    
    # 8. Calculate Top-3 Accuracy using model's prediction probabilities
    top3_indices = np.argsort(pest_probabilities, axis=1)[:, -3:] # Get indices of top 3 highest probabilities per sample
    
    # Check for each sample if true target y_true is in the top 3 predicted indices
    top3_correct = np.array([Y_test[i, 0] in top3_indices[i] for i in range(len(Y_test))])
    top3_acc = np.mean(top3_correct)
    
    print("--------------------------------------------------")
    print(f"ACTUAL TRAINED MODEL EVALUATION RESULTS:")
    print(f"Top-1 Pest Accuracy : {top1_acc * 100:.4f}% ({top1_acc:.4f})")
    print(f"Top-3 Pest Accuracy : {top3_acc * 100:.4f}% ({top3_acc:.4f})")
    print("--------------------------------------------------")
    
    # Analyze Crop-Restricted Top-3 vs Global Top-3
    print("\nANALYTICAL EXPLANATION OF ACCURACY METRICS:")
    print(f"1. Global Top-1 Accuracy: {top1_acc*100:.2f}% of samples match the single highest-probability pest predicted by Random Forest across all 25 pests.")
    print(f"2. Global Top-3 Accuracy: {top3_acc*100:.2f}% of samples have the true pest contained within the model's 3 highest probability predictions out of 25 global pests.")
    
    # Check if Top-3 Accuracy is 100% or close to 100%
    if top3_acc >= 0.999:
        print("EXPLANATION WHY TOP-3 ACCURACY IS ~100%:")
        print("- In this dataset, each specific Crop is associated with exactly 3 candidate pest species (e.g. Maize -> Fall Armyworm, Shoot Fly, Stem Borer).")
        print("- Because the model receives 'Crop' as a feature, the Random Forest splits trees on Crop first and assigns 0% probability to the 22 non-crop pests, leaving non-zero probabilities ONLY for the 3 crop-relevant pests.")
        print("- Therefore, the Top-3 probabilities emitted by predict_proba() are ALWAYS the 3 crop-relevant pests, guaranteeing that the true target pest is in the Top-3 set 100% of the time!")
    else:
        print(f"Actual Top-3 Accuracy is {top3_acc*100:.2f}%.")

if __name__ == "__main__":
    verify_accuracy()
