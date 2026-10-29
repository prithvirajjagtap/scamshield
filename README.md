# 🛡️ ScamShield — Fake Job & Internship Scam Detector

ScamShield is an NLP-based web application that analyzes job and internship postings to identify potentially fraudulent offers. It combines machine learning with rule-based scam indicators and provides an understandable risk assessment to help users make more informed decisions.

## Features

- **Three-level classification:** Labels job postings as *Looks Legit*, *Suspicious*, or *Likely Scam*.
- **ML-based prediction:** Uses TF-IDF features and Logistic Regression to estimate the likelihood of a posting belonging to the fake-job class.
- **Rule-based warnings:** Detects patterns associated with possible scams, such as registration fees, security deposits, suspicious contact methods, unrealistic earnings, and guaranteed selection claims.
- **Explainable predictions:** Displays influential text features associated with the ML prediction and highlights detected rule-based warnings.
- **Model comparison:** Evaluates Logistic Regression and Random Forest using precision, recall, F1-score, and ROC-AUC.
- **Class imbalance handling:** Uses balanced class weights because fake postings represent only a small proportion of the dataset.
- **Interactive web interface:** Built using Flask, HTML, CSS, and JavaScript.

## Tech Stack

- **Language:** Python
- **Machine learning and NLP:** scikit-learn, TF-IDF
- **Data processing:** pandas
- **Model persistence:** joblib
- **Backend:** Flask
- **Frontend:** HTML, CSS, JavaScript

## Project Structure

```text
scamshield/
├── app.py                  # Flask backend and prediction API
├── train_model.py          # Data preparation, training and evaluation
├── utils.py                # Shared text-cleaning function
├── requirements.txt        # Python dependencies
├── data/
│   └── fake_job_postings.csv
├── models/
│   ├── model.joblib        # Trained Logistic Regression model
│   ├── vectorizer.joblib   # Fitted TF-IDF vectorizer
│   └── metrics.json        # Model evaluation results
├── templates/
│   └── index.html          # Web application interface
└── static/
    ├── style.css
    └── script.js
```

## Dataset

ScamShield uses the **Fake Job Postings** dataset from Kaggle, commonly associated with the *Real / Fake Job Posting Prediction* dataset.

- Total postings: 17,879
- Fake postings: 865
- Approximate proportion of fake postings: 4.8%

The model combines the job title, company profile, description, requirements, and benefits into a single text input for training.

## How It Works

1. **Text preparation:** Combines relevant job-post fields and applies a shared text-cleaning function.
2. **Feature extraction:** Converts text into numerical TF-IDF features using unigrams and bigrams.
3. **Model training:** Trains Logistic Regression and Random Forest classifiers using a stratified train-test split and balanced class weights.
4. **Model selection:** Compares the models using precision, recall, F1-score, and ROC-AUC. Logistic Regression is selected for the deployed application.
5. **Prediction:** Estimates the probability of the fake-job class using the trained Logistic Regression model.
6. **Rule-based analysis:** Checks for common scam-related patterns and generates corresponding warnings.
7. **Risk assessment:** Combines the ML probability with a bounded rule-based adjustment to calculate a heuristic risk score.
8. **Results display:** Shows the classification, risk score, ML probability, rule-based warnings, and influential text features.

**Important:** The displayed risk score is a heuristic indicator, not a calibrated probability that a job is fraudulent. ML feature contributions indicate associations learned from training data; they do not prove that an individual word or posting is fraudulent.

## Model Evaluation

The following results are from the existing held-out test split recorded in `models/metrics.json`.

| Model | Precision | Recall | F1-score | ROC-AUC |
|---|---:|---:|---:|---:|
| Logistic Regression | 0.914 | 0.925 | 0.920 | 0.995 |
| Random Forest | 1.000 | 0.630 | 0.773 | 0.993 |

Logistic Regression was selected for deployment because it achieved a stronger recall and F1-score in this evaluation, while also supporting feature-level explanations.

These metrics describe performance on the held-out dataset split. They do not guarantee equivalent performance on new job postings, messaging-app offers, or scams that differ from the training data.

## Installation and Execution

### 1. Install Python dependencies

Open a terminal in the project directory:

```bash
pip install -r requirements.txt
```

### 2. Prepare the dataset

Download the Fake Job Postings dataset from Kaggle and place the CSV file at:

```text
data/fake_job_postings.csv
```

### 3. Train the models

Run this command if you need to regenerate the saved models and evaluation metrics:

```bash
python train_model.py
```

### 4. Start ScamShield

```bash
python app.py
```

Open the following address in your browser:

```text
http://127.0.0.1:5000
```

If the trained model files are already present in the `models/` directory, you can start the application without retraining.

## Limitations

- The training dataset consists primarily of formal English-language job postings.
- Real-world scams may use informal language, regional languages, images, or messaging-app conversations that differ from the training data.
- Rule-based patterns can produce false positives or miss new scam techniques.
- ML probabilities and feature contributions are estimates learned from the training data, not proof of fraud.
- The model has not been demonstrated to generalize to every job platform or scam type.

ScamShield is a decision-support tool, not a guarantee of legitimacy. Always verify employers through official channels, and never pay money to secure a job or internship.

## Screenshots

Add screenshots of the running application to demonstrate its main functionality:

1. **Potential scam example:** Show the classification, risk assessment, and detected warnings.
2. **Legitimate example:** Show a normal job or internship posting and its results.

## Future Improvements

Potential improvements include evaluating the model on newer, independently collected job postings, testing additional text-classification approaches, and improving handling of negation and previously unseen scam patterns.
