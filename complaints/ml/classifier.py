from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Iterable

from joblib import dump, load
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


@dataclass(frozen=True)
class ComplaintPrediction:
    department_code: str
    priority: str


def _build_training_data_from_seed() -> Tuple[Iterable[str], Iterable[str], Iterable[str]]:
    """
    Built‑in demo training set based on the departments in the UI.

    Used when no external CSV training data is provided.
    Department codes here MUST match `Department.code` in `complaints.models`.
    """
    samples = [
        # Municipal - Roads / PWD
        ("road is broken with many potholes on the street", "MC-PWD", "HIGH"),
        ("streetlights not working on my road", "MC-PWD", "MEDIUM"),
        ("footpath damaged and unsafe for walking", "MC-PWD", "MEDIUM"),
        ("big pothole causing accidents", "MC-PWD", "CRITICAL"),
        # Municipal - Water
        ("no water supply in my area", "MC-WATER", "HIGH"),
        ("water leakage from main pipeline", "MC-WATER", "HIGH"),
        ("very low water pressure in taps", "MC-WATER", "MEDIUM"),
        ("dirty contaminated water coming from tap", "MC-WATER", "CRITICAL"),
        # Solid Waste
        ("garbage not collected from street", "MC-SWM", "HIGH"),
        ("dustbin overflowing and bad smell", "MC-SWM", "MEDIUM"),
        ("no street cleaning from many days", "MC-SWM", "MEDIUM"),
        # Health / Sanitation
        ("mosquito breeding due to stagnant water", "MC-HEALTH", "HIGH"),
        ("dispensary not functioning properly", "MC-HEALTH", "MEDIUM"),
        ("dirty public toilet not cleaned", "MC-HEALTH", "MEDIUM"),
        # Sewerage / Drainage
        ("manhole open and dangerous", "MC-SEWER", "CRITICAL"),
        ("sewer water overflowing on road", "MC-SEWER", "HIGH"),
        ("drainage blocked causing waterlogging", "MC-SEWER", "HIGH"),
        # Electricity
        ("frequent power cuts in my locality", "STATE-ELEC", "HIGH"),
        ("transformer making noise and sparking", "STATE-ELEC", "CRITICAL"),
        ("electricity bill is wrong and very high", "STATE-ELEC", "MEDIUM"),
        # PHED
        ("village water scheme not working", "STATE-PHED", "HIGH"),
        ("handpump water contaminated", "STATE-PHED", "CRITICAL"),
        # PWD Roads (State)
        ("highway full of potholes", "STATE-PWD", "HIGH"),
        ("bridge damage visible cracks", "STATE-PWD", "CRITICAL"),
        # Traffic Police
        ("traffic signal not working at junction", "POLICE-TRAF", "HIGH"),
        ("illegal parking blocking road", "POLICE-TRAF", "MEDIUM"),
        # Fire
        ("fire safety violation in building", "MC-FIRE", "CRITICAL"),
        ("fire hydrant not working", "MC-FIRE", "HIGH"),
        # District Health
        ("government hospital staff not available", "DIST-HEALTH", "MEDIUM"),
        ("ambulance not coming on time", "DIST-HEALTH", "HIGH"),
        # Pollution Control
        ("factory releasing toxic smoke and pollution", "STATE-POLL", "CRITICAL"),
        ("construction dust causing breathing problem", "STATE-POLL", "HIGH"),
        # Food & Civil Supplies
        ("ration shop not giving full quantity", "STATE-FCS", "HIGH"),
        ("pds shop closed for many days", "STATE-FCS", "MEDIUM"),
        # Local Police
        ("loud noise at night disturbing area", "POLICE-LOCAL", "MEDIUM"),
        ("chain snatching incident report", "POLICE-LOCAL", "HIGH"),
        # Consumer Forum
        ("internet provider not resolving service issue", "JUD-CONS", "MEDIUM"),
        ("billing dispute with electricity company", "JUD-CONS", "MEDIUM"),
        # Revenue
        ("property tax calculation wrong", "DIST-REV", "MEDIUM"),
        ("name not updated in land records", "DIST-REV", "MEDIUM"),
        # Town Planning
        ("illegal encroachment on government land", "MC-TP", "HIGH"),
        ("building constructed without permission", "MC-TP", "HIGH"),
        # Parks & Gardens
        ("park lights not working", "MC-PARK", "LOW"),
        ("playground equipment broken", "MC-PARK", "MEDIUM"),
    ]
    texts = [s[0] for s in samples]
    dept_labels = [s[1] for s in samples]
    priority_labels = [s[2] for s in samples]
    return texts, dept_labels, priority_labels


def load_training_data_from_csv(csv_path: Path) -> Tuple[Iterable[str], Iterable[str], Iterable[str]]:
    """
    Load training data from a CSV file.

    Expected columns:
      - `text`: complaint description
      - `department_code`: target `Department.code`
      - `priority`: one of LOW / MEDIUM / HIGH / CRITICAL

    If the file or columns are missing, this will raise, and the caller
    can fall back to the seed data.
    """
    df = pd.read_csv(csv_path)
    required_cols = {"text", "department_code", "priority"}
    missing = required_cols.difference(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

    texts = df["text"].astype(str).tolist()
    dept_labels = df["department_code"].astype(str).tolist()
    priority_labels = df["priority"].astype(str).tolist()
    return texts, dept_labels, priority_labels


_MODEL_DIR = Path(__file__).resolve().parent / "artifacts"
_DEPT_MODEL_PATH = _MODEL_DIR / "department_pipeline.joblib"
_PRIORITY_MODEL_PATH = _MODEL_DIR / "priority_pipeline.joblib"

_department_pipeline: Optional[Pipeline] = None
_priority_pipeline: Optional[Pipeline] = None


def _load_or_train_models() -> None:
    """
    Model lifecycle:
    - Try to load serialized pipelines from disk.
    - If not present, train once using CSV if available, otherwise seed data.
    """
    global _department_pipeline, _priority_pipeline

    if _department_pipeline is not None and _priority_pipeline is not None:
        return

    try:
        if _DEPT_MODEL_PATH.exists() and _PRIORITY_MODEL_PATH.exists():
            _department_pipeline = load(_DEPT_MODEL_PATH)
            _priority_pipeline = load(_PRIORITY_MODEL_PATH)
            return
    except Exception:
        # If loading fails, fall back to training.
        _department_pipeline = None
        _priority_pipeline = None

    # Try CSV-based training first
    texts: Iterable[str]
    dept_labels: Iterable[str]
    priority_labels: Iterable[str]
    csv_path = _MODEL_DIR / "complaints_training_data.csv"
    try:
        if csv_path.exists():
            texts, dept_labels, priority_labels = load_training_data_from_csv(csv_path)
        else:
            texts, dept_labels, priority_labels = _build_training_data_from_seed()
    except Exception:
        texts, dept_labels, priority_labels = _build_training_data_from_seed()

    dept_pipe: Pipeline = Pipeline(
        [("tfidf", TfidfVectorizer(stop_words="english")), ("clf", MultinomialNB())]
    )
    dept_pipe.fit(texts, dept_labels)

    priority_pipe: Pipeline = Pipeline(
        [("tfidf", TfidfVectorizer(stop_words="english")), ("clf", MultinomialNB())]
    )
    priority_pipe.fit(texts, priority_labels)

    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    try:
        dump(dept_pipe, _DEPT_MODEL_PATH)
        dump(priority_pipe, _PRIORITY_MODEL_PATH)
    except Exception:
        # If saving fails we still keep the in-memory models.
        pass

    _department_pipeline = dept_pipe
    _priority_pipeline = priority_pipe


def predict_department_and_priority(text: str) -> ComplaintPrediction:
    """
    Predict department code and priority level for a complaint.

    If anything goes wrong, this falls back to a generic
    Helpline department with MEDIUM priority so that the
    complaint is never lost.
    """
    try:
        _load_or_train_models()

        cleaned = (text or "").strip()
        if not cleaned:
            return ComplaintPrediction(department_code="HELP", priority="MEDIUM")

        dept = _department_pipeline.predict([cleaned])[0]
        priority = _priority_pipeline.predict([cleaned])[0]
        return ComplaintPrediction(department_code=str(dept), priority=str(priority))
    except Exception:
        # Safe fallback – route to helpline
        return ComplaintPrediction(department_code="HELP", priority="MEDIUM")

