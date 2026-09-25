import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from analytics.pipeline import classifier


def test_train_only_imputation_and_unknown_category(tmp_path):
    train = pd.DataFrame({'pclass':[1,2,3,3,1,2], 'age':[20,30,np.nan,40,50,60],
                          'sibsp':[0,1,0,1,0,1], 'parch':[0,0,0,1,1,0],
                          'fare':[10,20,30,40,50,60], 'sex':['male','female']*3,
                          'embarked':['S','C','Q','S','C','S']})
    model = classifier(LogisticRegression()).fit(train, [0,1,0,1,1,0])
    imputer = model['preprocess'].named_transformers_['numeric']['imputer']
    assert imputer.statistics_[1] == 40
    before = imputer.statistics_.copy()
    test = train.iloc[:2].copy()
    test['age'] = [np.nan,9999]
    test['embarked'] = 'UNSEEN'
    prediction = model.predict(test)
    np.testing.assert_array_equal(before, imputer.statistics_)
    artifact = tmp_path / 'full.joblib'
    joblib.dump(model, artifact)
    np.testing.assert_array_equal(prediction, joblib.load(artifact).predict(test))
