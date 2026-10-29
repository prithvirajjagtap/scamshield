
import json
import re
from pathlib import Path

import joblib
from flask import Flask, jsonify, render_template, request

from utils import clean_text

# Resolve files relative to this project, not the terminal's current directory.
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1 MB request limit

vectorizer = joblib.load(MODEL_DIR / "vectorizer.joblib")
model = joblib.load(MODEL_DIR / "model.joblib")
feature_names = vectorizer.get_feature_names_out()
coef = model.coef_[0]

try:
    with (MODEL_DIR / "metrics.json").open(encoding="utf-8") as f:
        METRICS = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    METRICS = {}

# These are warning patterns, not proof that a job is fraudulent.
RULES = [
    (
        r"\bregistration\s+(?:fee|amount|charges?)\b",
        "Asks for a registration fee",
        "fee",
    ),
    (
        r"\bsecurity\s+deposit\b",
        "Asks for a security deposit",
        "deposit",
    ),
    (
        r"\b(?:pay|deposit|transfer)\b[^.!?\n]{0,60}"
        r"\b(?:fee|amount|money|rs\.?|inr|₹)\b",
        "Asks you to pay money",
        "payment",
    ),
    (
        r"\bno\s+(?:interview|experience|skills?)\s+(?:needed|required)\b",
        "Promises a job with no interview/experience",
        None,
    ),
    (
        r"\bearn\s+(?:up\s+to\s+)?(?:rs\.?|inr|₹|\$)?\s?"
        r"\d[\d,]*\s?(?:/|per)\s?(?:day|week|hour)\b",
        "Unrealistic daily/weekly earnings",
        None,
    ),
    (
        r"\b(?:whatsapp|telegram)\b",
        "Contact via WhatsApp/Telegram",
        None,
    ),
    (
        r"\b[\w.+-]+@(gmail|yahoo|outlook|hotmail)\.com\b",
        "Uses a free personal email instead of a company domain",
        None,
    ),
    (
        r"\b(?:limited\s+(?:seats|slots|vacancies)|only\s+\d+\s+(?:seats|slots|vacancies))\b",
        "Possible urgency pressure (limited seats)",
        None,
    ),
    (
        r"\b(?:urgent|immediate)\s+(?:joining|hiring|requirement)\b",
        "Pressure to join immediately",
        None,
    ),
    (
        r"\b(?:guaranteed|100%)\s+(?:job|placement|selection)\b",
        "Guaranteed selection claim",
        None,
    ),
]

# Explicit negations that can cancel fee/deposit/payment warnings.
NEGATION_PATTERNS = [
    r"\bno\b",
    r"\bnot\b",
    r"\bnever\b",
    r"\bwithout\b",
    r"\bdoes\s+not\b",
    r"\bdo\s+not\b",
    r"\bdoesn't\b",
    r"\bdon't\b",
    r"\bwaived\b",
    r"\bfree\s+of\b",
    r"\b(?:is|are)\s+not\s+required\b",
    r"\bnot\s+required\b",
]

def is_payment_warning_negated(text, match_start, category):
    """Avoid common false warnings when the matched demand is explicitly negated."""
    if category is None:
        return False

    # Look at the sentence containing the match, not the whole document.
    left_boundary = max(
        text.rfind(".", 0, match_start),
        text.rfind("!", 0, match_start),
        text.rfind("?", 0, match_start),
        text.rfind("\n", 0, match_start),
    )
    sentence_start = left_boundary + 1
    prefix = text[sentence_start:match_start].lower()

    # Negation must be close to the matched phrase to reduce accidental suppression.
    prefix = prefix[-100:]
    return any(re.search(pattern, prefix) for pattern in NEGATION_PATTERNS)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/metrics")
def metrics():
    return jsonify(METRICS)


@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Please send the job description as JSON."}), 400

    raw_text = data.get("text")
    if not isinstance(raw_text, str):
        return jsonify({"error": "Job description must be text."}), 400

    text = raw_text.strip()

    if len(text) < 30:
        return jsonify({
            "error": "Please paste at least a couple of sentences of the job post."
        }), 400

    if len(text) > 20000:
        return jsonify({
            "error": "Please keep the job description under 20,000 characters."
        }), 400

    # ML probability: based on the trained Logistic Regression model.
    X = vectorizer.transform([clean_text(text)])
    probabilities = model.predict_proba(X)[0]
    classes = list(model.classes_)

    # Identify the probability belonging to the fraudulent class (label 1).
    if 1 not in classes:
        return jsonify({"error": "The loaded model does not contain the fraud class."}), 500

    ml_prob = float(probabilities[classes.index(1)])

    # Approximate feature contributions for the linear Logistic Regression model.
    coo = X.tocoo()
    contributions = sorted(
        (
            (feature_names[col], float(value * coef[col]))
            for col, value in zip(coo.col, coo.data)
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    red_words = [
        {"word": word, "weight": round(weight, 3)}
        for word, weight in contributions
        if weight > 0.02
    ][:8]

    safe_words = [
        {"word": word, "weight": round(abs(weight), 3)}
        for word, weight in contributions
        if weight < -0.02
    ][:5]

    # Collect distinct rule warnings, skipping common explicit negations.
    rule_hits = []
    for pattern, label, category in RULES:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            if is_payment_warning_negated(text, match.start(), category):
                continue

            rule_hits.append({
                "label": label,
                "match": match.group(0),
            })
            break

    # This is a heuristic indicator, NOT a calibrated fraud probability.
    # Keep the ML probability available separately in the response.
    rule_adjustment = min(0.30, 0.05 * len(rule_hits))
    risk_score = min(1.0, ml_prob + rule_adjustment)

    if risk_score >= 0.60:
        verdict = "Likely Scam"
    elif risk_score >= 0.30:
        verdict = "Suspicious"
    else:
        verdict = "Looks Legit"

    return jsonify({
        "verdict": verdict,
        "score": round(risk_score * 100, 1),
        "ml_probability": round(ml_prob * 100, 1),
        "rule_adjustment": round(rule_adjustment * 100, 1),
        "score_type": "heuristic_risk_score",
        "red_words": red_words,
        "safe_words": safe_words,
        "rule_flags": rule_hits,
    })


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "Request is too large. Please shorten the text."}), 413


if __name__ == "__main__":
    app.run(debug=True)
