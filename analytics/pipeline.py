"""One Titanic load, auditable EDA, train-only ML, and Markdown results."""
import argparse
import io
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score, recall_score,
                             roc_auc_score, RocCurveDisplay)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, plot_tree

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parent / 'runtime'
NUM = ['pclass', 'age', 'sibsp', 'parch', 'fare']
CAT = ['sex', 'embarked']
SEED = 42


def preprocessing(numeric=NUM):
    return ColumnTransformer([
        ('numeric', Pipeline([('imputer', SimpleImputer(strategy='median')),
                              ('scaler', StandardScaler())]), numeric),
        ('categorical', Pipeline([('imputer', SimpleImputer(strategy='most_frequent')),
                                  ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False,
                                                           drop='first'))]), CAT)])


def classifier(estimator):
    return Pipeline([('preprocess', preprocessing()), ('model', estimator)])


def metrics(model, x, y):
    prediction = model.predict(x)
    return dict(accuracy=accuracy_score(y, prediction), precision=precision_score(y, prediction, zero_division=0),
                recall=recall_score(y, prediction, zero_division=0), f1=f1_score(y, prediction, zero_division=0),
                auc=roc_auc_score(y, model.predict_proba(x)[:, 1]))


def run(offline=False):
    RUNTIME.mkdir(exist_ok=True)
    fallback = HERE / 'titanic.csv'
    # Exactly one Seaborn load in this module; modeling never reloads the data.
    if offline:
        raw = pd.read_csv(fallback)
        origin = 'Committed offline CSV'
    else:
        try:
            raw = sns.load_dataset('titanic')
            raw.to_csv(fallback, index=False)
            origin = "sns.load_dataset('titanic'), saved immediately as titanic.csv"
        except (OSError, ConnectionError):
            if not fallback.exists():
                raise
            raw = pd.read_csv(fallback)
            origin = 'Committed CSV after network/cache failure'
    notes = ['# Executed Titanic analysis', f'Data source: {origin}. Seed: {SEED}.']

    def section(title, content):
        notes.extend([f'## {title}', content])

    info = io.StringIO()
    raw.info(buf=info)
    section('Profile', f'Shape: {raw.shape}.\n\n```text\n{info.getvalue()}\n```\n\n' + raw.describe().to_markdown())
    missing = raw.isna().mean() * 100
    decisions = []
    cleaned = raw.copy()
    sparse = missing[(missing > 0) & (missing < 5)].index.tolist()
    cleaned = cleaned.dropna(subset=sparse).copy()
    for col, pct in missing[missing > 0].items():
        if pct < 5:
            strategy = 'Under 5%: drop rows missing this field; very few rows are lost.'
        elif pct <= 30:
            strategy = '5–30%: median imputation; training-only statistics for modeling.'
        else:
            cleaned = cleaned.drop(columns=col)
            strategy = 'Over 30%: drop column; extensive missingness makes imputation unreliable.'
        decisions.append({'column': col, 'missing_percent': pct, 'strategy': strategy})
    section('Missingness decisions', pd.DataFrame(decisions).to_markdown(index=False, floatfmt='.4f') +
            f'\n\nRows retained: {len(cleaned)} of {len(raw)}. The sparse-column row mask is applied once.')
    # Split BEFORE estimating even the EDA imputation value. Retain the original missing-age mask
    # so each CV fold can estimate its own median, rather than reuse a pre-CV value.
    train_ids, test_ids = train_test_split(cleaned.index, test_size=.2, random_state=SEED,
                                          stratify=cleaned.survived)
    missing_age = cleaned.age.isna()
    median_age = cleaned.loc[train_ids, 'age'].median()
    cleaned['age'] = cleaned.age.fillna(median_age)
    section('Split and leakage controls',
            f'Survived: {raw.survived.mean():.2%}; did not survive: {1-raw.survived.mean():.2%}. '
            f'Stratification preserves this unequal balance in the {len(train_ids)}/{len(test_ids)} split. '
            f'EDA fills age with the training-row median {median_age:.2f}. Modeling uses the same cleaned '
            'rows and columns, restoring only the saved missing-age mask so each training/CV fold fits '
            'its own imputer. Numeric median imputation, categorical mode imputation, one-hot encoding, '
            'and scaling are fitted within each pipeline. No EDA z-scores feed modeling. '
            'alive directly reveals the label; class, who, adult_male, alone, embark_town duplicate other '
            'features and are excluded. The high-missingness deck field is excluded.')
    fig, axes = plt.subplots(3, 4, figsize=(22, 15))
    outliers = []
    for i, col in enumerate(['age', 'fare']):
        sns.histplot(cleaned[col], kde=True, ax=axes[0, 2*i])
        sns.boxplot(x=cleaned[col], ax=axes[0, 2*i+1])
        q1, q3 = cleaned[col].quantile([.25, .75])
        iqr = q3 - q1
        count = int(((cleaned[col] < q1-1.5*iqr) | (cleaned[col] > q3+1.5*iqr)).sum())
        outliers.append(dict(column=col, q1=q1, q3=q3, lower=q1-1.5*iqr, upper=q3+1.5*iqr, outliers=count))
    section('Univariate distributions and IQR outliers', pd.DataFrame(outliers).to_markdown(index=False) +
            '\n\nOutliers use the cleaned, imputed data and are retained: high fares can be legitimate, '
            'and removing them would erase socioeconomic variation. Age is concentrated among adults; '
            'the age histogram has an imputation peak at the median.')
    fare_mean, fare_median, fare_mode = cleaned.fare.mean(), cleaned.fare.median(), cleaned.fare.mode().iloc[0]
    section('Fare skewness', f'Mean {fare_mean:.4f} > median {fare_median:.4f} > mode {fare_mode:.4f}: '
            'fare is right-skewed, consistent with a few expensive tickets pulling up the mean. '
            'The long upper tail is also apparent in the fare histogram and box plot.')
    rates = []
    for sex in ['female', 'male', 'all']:
        for cls in [1, 2, 3, 'all']:
            if sex == 'all' and cls == 'all':
                continue
            mask = ((cleaned.sex == sex) | (sex == 'all')) & ((cleaned.pclass == cls) | (cls == 'all'))
            rates.append(dict(sex=sex, pclass=cls, n=int(mask.sum()), survival_rate=cleaned.loc[mask, 'survived'].mean()))
    section('Boolean-mask survival breakdowns', pd.DataFrame(rates).to_markdown(index=False, floatfmt='.4f'))
    cols = ['survived', 'pclass', 'age', 'sibsp', 'parch', 'fare']
    corr = cleaned[cols].corr()
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='vlag', vmin=-1, vmax=1, ax=axes[1, 0])
    pairs = sorted([(a, b, corr.loc[a, b]) for i, a in enumerate(cols) for b in cols[i+1:]],
                   key=lambda item: abs(item[2]), reverse=True)
    explanations = {
        frozenset(['pclass', 'fare']): 'Higher numerical class denotes cheaper travel classes, explaining the negative association with fare.',
        frozenset(['sibsp', 'parch']): 'Passengers traveling with siblings/spouses also tend to travel with parents/children.',
        frozenset(['pclass', 'age']): 'Older passengers tend to travel in lower-numbered, higher-status classes.'}
    section('Chart 1 — six-column correlation heatmap', corr.to_markdown(floatfmt='.4f') + '\n\n' + ' '.join(
        f'{a} versus {b}: r={value:.4f}. ' + explanations.get(frozenset([a,b]), 'This is association, not a causal effect.')
        for a,b,value in pairs[:2]) + ' These are the two largest absolute correlations among unique off-diagonal pairs; '
        'boolean adult_male and alone are excluded.')
    sns.barplot(data=cleaned, x='pclass', y='survived', hue='sex', errorbar=None, ax=axes[1, 1])
    axes[1, 1].set_title('Survival by sex and ticket class')
    sex_rates = cleaned.groupby('sex').survived.mean()
    section('Chart 2 — sex and class survival',
            f'Female survival is {sex_rates["female"]:.2%}, versus {sex_rates["male"]:.2%} for males. '
            'The grouped bars show whether that disparity persists within ticket class. '
            'This is consistent with differences in evacuation access, but the observational data cannot establish causation.')
    sns.boxplot(data=cleaned, x='pclass', y='fare', hue='survived', ax=axes[1, 2])
    section('Chart 3 — fare, class, and outcome',
            f'Median fare among survivors is {cleaned.loc[cleaned.survived == 1, "fare"].median():.2f}, '
            f'compared with {cleaned.loc[cleaned.survived == 0, "fare"].median():.2f} among non-survivors. '
            'Class-stratified boxes help distinguish ticket-class differences from variation within each class. '
            'Long tails and overlapping boxes show that fare alone does not determine survival.')
    sns.scatterplot(data=cleaned, x='age', y='fare', hue='survived', style='sex', alpha=.65, ax=axes[1, 3])
    section('Chart 4 — age, fare, sex, and outcome',
            'Survivors and non-survivors overlap across age and fare, so a simple age or fare cutoff is insufficient. '
            'Sex markers add a third explanatory feature to the comparison. The vertical median-age band '
            'partly reflects imputation and should not be read as an actual age-frequency spike.')
    z = (cleaned[['age','fare']] - cleaned[['age','fare']].mean()) / cleaned[['age','fare']].std(ddof=0)
    standard = pd.DataFrame({'before_mean': cleaned[['age','fare']].mean(),
                             'before_std_population': cleaned[['age','fare']].std(ddof=0),
                             'after_mean': z.mean(), 'after_std_population': z.std(ddof=0)})
    section('Exploratory standardization', standard.to_markdown(floatfmt='.6f') +
            '\n\nComputed as z=(x−mean)/std with population std (ddof=0), matching StandardScaler. '
            'This full-frame diagnostic is isolated from all modeling.')
    modeling = cleaned.copy()
    modeling.loc[missing_age, 'age'] = np.nan
    x, y = modeling[NUM + CAT], modeling.survived
    xtrain, xtest, ytrain, ytest = x.loc[train_ids], x.loc[test_ids], y.loc[train_ids], y.loc[test_ids]
    estimators = {
        'Logistic Regression': LogisticRegression(max_iter=2000, random_state=SEED),
        'Decision Tree': DecisionTreeClassifier(max_depth=4, min_samples_leaf=5, random_state=SEED),
        'Random Forest': RandomForestClassifier(n_estimators=150, max_depth=8, random_state=SEED, n_jobs=1)}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    models, scores, cv_scores = {}, {}, {}
    for name, estimator in estimators.items():
        model = classifier(estimator)
        cv_scores[name] = float(cross_val_score(model, xtrain, ytrain, scoring='f1', cv=cv).mean())
        models[name] = model.fit(xtrain, ytrain)
        scores[name] = metrics(model, xtest, ytest)
        RocCurveDisplay.from_estimator(model, xtest, ytest, name=name, ax=axes[2, 0])
    section('Classifier test comparison', pd.DataFrame(scores).T.to_markdown(floatfmt='.4f') +
            '\n\nConfusion matrices use rows=true, columns=predicted, label order [0, 1].\n\n' +
            '\n\n'.join(f'{name}: `{confusion_matrix(ytest, model.predict(xtest)).tolist()}`' for name,model in models.items()))
    plot_tree(models['Decision Tree']['model'],
              feature_names=models['Decision Tree']['preprocess'].get_feature_names_out(),
              class_names=['Died', 'Survived'], filled=True, ax=axes[2, 1], fontsize=4)
    variants = {'Baseline': clone(models['Logistic Regression']),
                'Balanced': classifier(LogisticRegression(max_iter=2000, class_weight='balanced', random_state=SEED)),
                'SMOTE': ImbPipeline([('preprocess', preprocessing()), ('smote', SMOTE(random_state=SEED)),
                                      ('model', LogisticRegression(max_iter=2000, random_state=SEED))])}
    imbalance = {}
    for name, model in variants.items():
        model.fit(xtrain, ytrain)
        imbalance[name] = {k:v for k,v in metrics(model, xtest, ytest).items() if k in ['precision','recall','f1']}
    best_imb = max(imbalance, key=lambda name: imbalance[name]['f1'])
    section('Imbalance handling', pd.DataFrame(imbalance).T.to_markdown(floatfmt='.4f') +
            f'\n\n{best_imb} has the highest held-out F1 ({imbalance[best_imb]["f1"]:.4f}), balancing precision and recall. '
            'SMOTE is called only in fit on training rows; never on held-out rows. '
            'Interpolation after one-hot encoding can create fractional indicator values, so this is the required '
            'SMOTE baseline rather than a claim of realistic synthetic passengers. These comparisons are exploratory, '
            'not used to select the deployed model using the test set.')
    search = GridSearchCV(classifier(RandomForestClassifier(oob_score=True, bootstrap=True, random_state=SEED, n_jobs=1)),
                          {'model__n_estimators':[100,200], 'model__max_depth':[5,None],
                           'model__max_features':['sqrt', .8]}, cv=cv, scoring='f1', n_jobs=1)
    search.fit(xtrain, ytrain)
    models['Tuned Random Forest'] = search.best_estimator_
    scores['Tuned Random Forest'] = metrics(search.best_estimator_, xtest, ytest)
    cv_scores['Tuned Random Forest'] = float(search.best_score_)
    section('Random Forest grid search',
            f'Best parameters: `{json.dumps(search.best_params_, sort_keys=True)}`. '
            f'Best five-fold training CV F1: {search.best_score_:.4f}. '
            f'Refitted training OOB score: {search.best_estimator_["model"].oob_score_:.4f}. '
            'OOB is a diagnostic accuracy, not a held-out test score; upstream preprocessing is fitted on the '
            'whole training split for this refit. The untouched test metrics are reported separately.')
    reg_num = ['pclass','age','sibsp','parch']
    regression = Pipeline([('preprocess', preprocessing(reg_num)), ('model', LinearRegression())])
    # Same row split; fare removed from inputs. Survival and redundant derived features are excluded.
    regression.fit(modeling.loc[train_ids, reg_num+CAT], modeling.loc[train_ids, 'fare'])
    predicted = regression.predict(modeling.loc[test_ids, reg_num+CAT])
    actual = modeling.loc[test_ids, 'fare']
    r2 = r2_score(actual, predicted)
    n = len(test_ids)
    p = regression['preprocess'].transform(modeling.loc[test_ids, reg_num+CAT]).shape[1]
    reg_metrics = dict(MAE=mean_absolute_error(actual, predicted), RMSE=np.sqrt(mean_squared_error(actual, predicted)),
                       R2=r2, Adjusted_R2=1-(1-r2)*(n-1)/(n-p-1))
    residual = actual.to_numpy()-predicted
    axes[2, 2].scatter(predicted, residual, alpha=.6)
    axes[2, 2].axhline(0, color='black', linestyle='--')
    axes[2, 2].set(xlabel='Predicted fare', ylabel='Residual (actual − predicted)', title='Regression residuals')
    bins = pd.qcut(predicted, 3, duplicates='drop')
    spread = pd.DataFrame({'predicted_bin':bins, 'residual':residual}).groupby('predicted_bin', observed=True).residual.std()
    ratio = float(spread.max()/spread.min())
    section('Fare regression and residuals', pd.DataFrame([reg_metrics], index=['Linear Regression']).to_markdown(floatfmt='.4f')+
            f'\n\nAdjusted R² uses n={n} test rows and p={p} encoded predictors (excluding intercept). '
            f'Residual standard deviations by predicted-fare tercile: {spread.round(3).to_dict()}; max/min={ratio:.2f}. '
            + ('The unequal spread is consistent with heteroscedasticity.' if ratio > 2 else
               'This diagnostic does not show strong heteroscedasticity; inspect the plot for local patterns.') +
            ' This is an exploratory diagnostic, not a formal hypothesis test. Fare is not used as an input; '
            'the same cleaned cohort and age-missingness provenance are retained.')
    comparison = pd.DataFrame(scores).T.add_prefix('Classification: ')
    for key,value in reg_metrics.items():
        comparison.loc['Linear Regression', 'Regression: '+key] = value
    section('Final comparison — distinct metric groups', comparison.fillna('—').to_markdown())
    winner = max(cv_scores, key=cv_scores.get)
    s = scores[winner]
    section('Deployment recommendation',
            f'I would deploy {winner}, selected by training-only cross-validation F1 ({cv_scores[winner]:.4f}). '
            f'Its held-out accuracy is {s["accuracy"]:.4f}, precision {s["precision"]:.4f}, recall {s["recall"]:.4f}, '
            f'F1 {s["f1"]:.4f}, and ROC AUC {s["auc"]:.4f}. '
            'This criterion gives both missed survivors and false positive predictions weight rather than maximizing accuracy alone. '
            'A new external evaluation cohort and calibration check are needed before using this educational model in a real setting. '
            'Selection did not maximize held-out test scores; the grid-search CV winner may still have tuning optimism.')
    section('Training CV selection scores', pd.Series(cv_scores, name='mean_training_CV_F1').to_frame().to_markdown())
    joblib.dump(models[winner], RUNTIME / 'best_pipeline.joblib')
    reloaded = joblib.load(RUNTIME / 'best_pipeline.joblib')
    np.testing.assert_array_equal(models[winner].predict(xtest), reloaded.predict(xtest))
    section('Saved pipeline reload', 'PASS: joblib reload produces identical predictions on all raw test inputs, including missing ages. '
            'The artifact contains the fitted ColumnTransformer and classifier together. Run `python analytics/predict.py` '
            'to demonstrate raw-input inference. The artifact is regenerated under runtime/ to avoid committing binary model files.')
    axes[2, 3].axis('off')
    axes[2, 3].text(.05,.8, f'Champion: {winner}\nTest F1: {s["f1"]:.3f}\nAUC: {s["auc"]:.3f}\nSeed: {SEED}', fontsize=13)
    fig.tight_layout()
    fig.savefig(HERE / 'charts.png', dpi=150)
    plt.close(fig)
    notes.insert(2, 'All required plots are consolidated in [charts.png](charts.png): row 1 univariate, '
                 'row 2 multivariate story, row 3 ROC, labeled tree, and residuals.')
    (HERE / 'RESULTS.md').write_text('\n\n'.join(notes)+'\n', encoding='utf-8')
    print(comparison.to_string())
    print(f'Saved full pipeline: {winner}; report: {HERE / "RESULTS.md"}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true')
    run(parser.parse_args().offline)
