"""
Train the ScamShield model.

Usage:
    1. Download 'fake_job_postings.csv' from Kaggle ("Real / Fake Job Posting Prediction")
    2. Put it in the data/ folder
    3. Run: python train_model.py
"""
import json
import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (classification_report, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split

from utils import clean_text

DATA_PATH = "data/fake_job_postings.csv"
TEXT_COLS = ["title", "company_profile", "description", "requirements", "benefits"]


def main():
    if not os.path.exists(DATA_PATH):
        raise SystemExit(f"Dataset not found at {DATA_PATH}. Download it from Kaggle first.")

    # 1. Load and combine text columns
    df = pd.read_csv(DATA_PATH)
    df[TEXT_COLS] = df[TEXT_COLS].fillna("")
    df["text"] = df[TEXT_COLS].agg(" ".join, axis=1).map(clean_text)
    df = df[df["text"].str.len() > 20]

    total, fake = len(df), int(df["fraudulent"].sum())
    print(f"Postings: {total} | Fake: {fake} ({fake / total:.1%}) -> imbalanced dataset")

    # 2. Split (stratified keeps the fake ratio equal in train and test)
    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["fraudulent"], test_size=0.2, random_state=42, stratify=df["fraudulent"]
    )

    # 3. TF-IDF features (unigrams + bigrams so phrases like "registration fee" are captured)
    vec = TfidfVectorizer(max_features=20000, ngram_range=(1, 2),
                          stop_words="english", min_df=3, sublinear_tf=True)
    Xtr = vec.fit_transform(X_train)
    Xte = vec.transform(X_test)

    # 4. Train and compare models. class_weight='balanced' handles the imbalance.
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, class_weight="balanced", C=5),
        "Random Forest": RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                                n_jobs=-1, random_state=42),
    }

    results = {}
    for name, model in models.items():
        model.fit(Xtr, y_train)
        pred = model.predict(Xte)
        proba = model.predict_proba(Xte)[:, 1]
        results[name] = {
            "precision": round(precision_score(y_test, pred), 3),
            "recall": round(recall_score(y_test, pred), 3),
            "f1": round(f1_score(y_test, pred), 3),
            "roc_auc": round(roc_auc_score(y_test, proba), 3),
        }
        print(f"\n===== {name} =====")
        print(classification_report(y_test, pred, target_names=["Real", "Fake"]))
        print("Confusion matrix:\n", confusion_matrix(y_test, pred))

    # 5. Serve Logistic Regression: its coefficients tell us WHICH words look scammy
    os.makedirs("models", exist_ok=True)
    joblib.dump(vec, "models/vectorizer.joblib")
    joblib.dump(models["Logistic Regression"], "models/model.joblib")

    with open("models/metrics.json", "w") as f:
        json.dump({"dataset_size": total, "fake_count": fake,
                   "served_model": "Logistic Regression", "results": results}, f, indent=2)

    print("\nSaved model, vectorizer and metrics to models/")


if __name__ == "__main__":
    main()
