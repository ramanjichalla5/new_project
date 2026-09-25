"""Reload the entire fitted pipeline and predict on raw, unscaled values."""
from pathlib import Path
import joblib
import pandas as pd

if __name__ == '__main__':
    model = joblib.load(Path(__file__).resolve().parents[1] / 'runtime' / 'best_pipeline.joblib')
    inputs = pd.DataFrame([{'pclass': 3, 'age': None, 'sibsp': 0, 'parch': 0,
                           'fare': 7.25, 'sex': 'male', 'embarked': 'S'},
                          {'pclass': 1, 'age': 38, 'sibsp': 1, 'parch': 0,
                           'fare': 71.28, 'sex': 'female', 'embarked': 'C'}])
    print('Raw-input predictions:', model.predict(inputs).tolist())
    print('Survival probabilities:', model.predict_proba(inputs)[:, 1].tolist())
