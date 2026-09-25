# Executed Titanic analysis

Data source: sns.load_dataset('titanic'), saved immediately as titanic.csv. Seed: 42.

All required plots are consolidated in [charts.png](charts.png): row 1 univariate, row 2 multivariate story, row 3 ROC, labeled tree, and residuals. The full-size labeled tree is [tree.png](tree.png).

## Profile

Shape: (891, 15).

```text
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 891 entries, 0 to 890
Data columns (total 15 columns):
 #   Column       Non-Null Count  Dtype   
---  ------       --------------  -----   
 0   survived     891 non-null    int64   
 1   pclass       891 non-null    int64   
 2   sex          891 non-null    object  
 3   age          714 non-null    float64 
 4   sibsp        891 non-null    int64   
 5   parch        891 non-null    int64   
 6   fare         891 non-null    float64 
 7   embarked     889 non-null    object  
 8   class        891 non-null    category
 9   who          891 non-null    object  
 10  adult_male   891 non-null    bool    
 11  deck         203 non-null    category
 12  embark_town  889 non-null    object  
 13  alive        891 non-null    object  
 14  alone        891 non-null    bool    
dtypes: bool(2), category(2), float64(2), int64(4), object(5)
memory usage: 80.7+ KB

```

|       |   survived |     pclass |      age |      sibsp |      parch |     fare |
|:------|-----------:|-----------:|---------:|-----------:|-----------:|---------:|
| count | 891        | 891        | 714      | 891        | 891        | 891      |
| mean  |   0.383838 |   2.30864  |  29.6991 |   0.523008 |   0.381594 |  32.2042 |
| std   |   0.486592 |   0.836071 |  14.5265 |   1.10274  |   0.806057 |  49.6934 |
| min   |   0        |   1        |   0.42   |   0        |   0        |   0      |
| 25%   |   0        |   2        |  20.125  |   0        |   0        |   7.9104 |
| 50%   |   0        |   3        |  28      |   0        |   0        |  14.4542 |
| 75%   |   1        |   3        |  38      |   1        |   0        |  31      |
| max   |   1        |   3        |  80      |   8        |   6        | 512.329  |

## Missingness decisions

| column      |   missing_percent | strategy                                                                  |
|:------------|------------------:|:--------------------------------------------------------------------------|
| age         |           19.8653 | 5–30%: median imputation; training-only statistics for modeling.          |
| embarked    |            0.2245 | Under 5%: drop rows missing this field; very few rows are lost.           |
| deck        |           77.2166 | Over 30%: drop column; extensive missingness makes imputation unreliable. |
| embark_town |            0.2245 | Under 5%: drop rows missing this field; very few rows are lost.           |

Rows retained: 889 of 891. The sparse-column row mask is applied once.

## Split and leakage controls

Survived: 38.38%; did not survive: 61.62%. Stratification preserves this unequal balance in the 711/178 split. EDA fills age with the training-row median 28.00. Modeling uses the same cleaned rows and columns, restoring only the saved missing-age mask so each training/CV fold fits its own imputer. Numeric median imputation, categorical mode imputation, one-hot encoding, and scaling are fitted within each pipeline. No EDA z-scores feed modeling. alive directly reveals the label; class, who, adult_male, alone, embark_town duplicate other features and are excluded. The high-missingness deck field is excluded.

## Univariate distributions and IQR outliers

| column   |      q1 |   q3 |    lower |   upper |   outliers |
|:---------|--------:|-----:|---------:|--------:|-----------:|
| age      | 22      |   35 |   2.5    | 54.5    |         65 |
| fare     |  7.8958 |   31 | -26.7605 | 65.6563 |        114 |

Outliers use the cleaned, imputed data and are retained: high fares can be legitimate, and removing them would erase socioeconomic variation. Age is concentrated among adults; the age histogram has an imputation peak at the median.

## Fare skewness

Mean 32.0967 > median 14.4542 > mode 8.0500: fare is right-skewed, consistent with a few expensive tickets pulling up the mean. The long upper tail is also apparent in the fare histogram and box plot.

## Boolean-mask survival breakdowns

| sex    | pclass   |   n |   survival_rate |
|:-------|:---------|----:|----------------:|
| female | 1        |  92 |          0.9674 |
| female | 2        |  76 |          0.9211 |
| female | 3        | 144 |          0.5000 |
| female | all      | 312 |          0.7404 |
| male   | 1        | 122 |          0.3689 |
| male   | 2        | 108 |          0.1574 |
| male   | 3        | 347 |          0.1354 |
| male   | all      | 577 |          0.1889 |
| all    | 1        | 214 |          0.6262 |
| all    | 2        | 184 |          0.4728 |
| all    | 3        | 491 |          0.2424 |

## Chart 1 — six-column correlation heatmap

|          |   survived |   pclass |     age |   sibsp |   parch |    fare |
|:---------|-----------:|---------:|--------:|--------:|--------:|--------:|
| survived |     1.0000 |  -0.3355 | -0.0698 | -0.0340 |  0.0832 |  0.2553 |
| pclass   |    -0.3355 |   1.0000 | -0.3365 |  0.0817 |  0.0168 | -0.5482 |
| age      |    -0.0698 |  -0.3365 |  1.0000 | -0.2325 | -0.1715 |  0.0937 |
| sibsp    |    -0.0340 |   0.0817 | -0.2325 |  1.0000 |  0.4145 |  0.1609 |
| parch    |     0.0832 |   0.0168 | -0.1715 |  0.4145 |  1.0000 |  0.2175 |
| fare     |     0.2553 |  -0.5482 |  0.0937 |  0.1609 |  0.2175 |  1.0000 |

pclass versus fare: r=-0.5482. Higher numerical class denotes cheaper travel classes, explaining the negative association with fare. sibsp versus parch: r=0.4145. Passengers traveling with siblings/spouses also tend to travel with parents/children. These are the two largest absolute correlations among unique off-diagonal pairs; boolean adult_male and alone are excluded.

## Chart 2 — sex and class survival

Female survival is 74.04%, versus 18.89% for males. The grouped bars show whether that disparity persists within ticket class. This is consistent with differences in evacuation access, but the observational data cannot establish causation.

## Chart 3 — fare, class, and outcome

Median fare among survivors is 26.00, compared with 10.50 among non-survivors. Class-stratified boxes help distinguish ticket-class differences from variation within each class. Long tails and overlapping boxes show that fare alone does not determine survival.

## Chart 4 — age, fare, sex, and outcome

Survivors and non-survivors overlap across age and fare, so a simple age or fare cutoff is insufficient. Sex markers add a third explanatory feature to the comparison. The vertical median-age band partly reflects imputation and should not be read as an actual age-frequency spike.

## Exploratory standardization

|      |   before_mean |   before_std_population |   after_mean |   after_std_population |
|:-----|--------------:|------------------------:|-------------:|-----------------------:|
| age  |     29.315152 |               12.977627 |     0.000000 |               1.000000 |
| fare |     32.096681 |               49.669545 |     0.000000 |               1.000000 |

Computed as z=(x−mean)/std with population std (ddof=0), matching StandardScaler. This full-frame diagnostic is isolated from all modeling.

## Classifier test comparison

|                     |   accuracy |   precision |   recall |     f1 |    auc |
|:--------------------|-----------:|------------:|---------:|-------:|-------:|
| Logistic Regression |     0.8146 |      0.7966 |   0.6912 | 0.7402 | 0.8610 |
| Decision Tree       |     0.7978 |      0.7759 |   0.6618 | 0.7143 | 0.8510 |
| Random Forest       |     0.8146 |      0.7966 |   0.6912 | 0.7402 | 0.8490 |

Confusion matrices use rows=true, columns=predicted, label order [0, 1].

Logistic Regression: `[[98, 12], [21, 47]]`

Decision Tree: `[[97, 13], [23, 45]]`

Random Forest: `[[98, 12], [21, 47]]`

## Imbalance handling

|          |   precision |   recall |     f1 |
|:---------|------------:|---------:|-------:|
| Baseline |      0.7966 |   0.6912 | 0.7402 |
| Balanced |      0.7083 |   0.7500 | 0.7286 |
| SMOTE    |      0.7463 |   0.7353 | 0.7407 |

SMOTE has the highest held-out F1 (0.7407), balancing precision and recall. SMOTE is called only in fit on training rows; never on held-out rows. Interpolation after one-hot encoding can create fractional indicator values, so this is the required SMOTE baseline rather than a claim of realistic synthetic passengers. These comparisons are exploratory, not used to select the deployed model using the test set.

## Random Forest grid search

Best parameters: `{"model__max_depth": null, "model__max_features": "sqrt", "model__n_estimators": 100}`. Best five-fold training CV F1: 0.7605. Refitted training OOB score: 0.8017. OOB is a diagnostic accuracy, not a held-out test score; upstream preprocessing is fitted on the whole training split for this refit. The untouched test metrics are reported separately.

## Fare regression and residuals

|                   |     MAE |    RMSE |     R2 |   Adjusted_R2 |
|:------------------|--------:|--------:|-------:|--------------:|
| Linear Regression | 19.6457 | 41.2628 | 0.3474 |        0.3205 |

Adjusted R² uses n=178 test rows and p=7 encoded predictors (excluding intercept). Residual standard deviations by predicted-fare tercile: {Interval(-4.444, 9.178, closed='right'): 7.292, Interval(9.178, 55.112, closed='right'): 11.309, Interval(55.112, 101.656, closed='right'): 68.516}; max/min=9.40. The unequal spread is consistent with heteroscedasticity. This is an exploratory diagnostic, not a formal hypothesis test. Fare is not used as an input; the same cleaned cohort and age-missingness provenance are retained.

## Final comparison — distinct metric groups

|                     | Classification: accuracy   | Classification: precision   | Classification: recall   | Classification: f1   | Classification: auc   | Regression: MAE   | Regression: RMSE   | Regression: R2      | Regression: Adjusted_R2   |
|:--------------------|:---------------------------|:----------------------------|:-------------------------|:---------------------|:----------------------|:------------------|:-------------------|:--------------------|:--------------------------|
| Logistic Regression | 0.8146067415730337         | 0.7966101694915254          | 0.6911764705882353       | 0.7401574803149606   | 0.8609625668449199    | —                 | —                  | —                   | —                         |
| Decision Tree       | 0.797752808988764          | 0.7758620689655172          | 0.6617647058823529       | 0.7142857142857143   | 0.8510026737967914    | —                 | —                  | —                   | —                         |
| Random Forest       | 0.8146067415730337         | 0.7966101694915254          | 0.6911764705882353       | 0.7401574803149606   | 0.8489973262032087    | —                 | —                  | —                   | —                         |
| Tuned Random Forest | 0.8033707865168539         | 0.7619047619047619          | 0.7058823529411765       | 0.732824427480916    | 0.8266042780748664    | —                 | —                  | —                   | —                         |
| Linear Regression   | —                          | —                           | —                        | —                    | —                     | 19.64569622850265 | 41.262754930048104 | 0.34737898460343164 | 0.3205063545576906        |

## Deployment recommendation

I would deploy Random Forest, selected by training-only cross-validation F1 (0.7650). Its held-out accuracy is 0.8146, precision 0.7966, recall 0.6912, F1 0.7402, and ROC AUC 0.8490. This criterion gives both missed survivors and false positive predictions weight rather than maximizing accuracy alone. A new external evaluation cohort and calibration check are needed before using this educational model in a real setting. Selection did not maximize held-out test scores; the grid-search CV winner may still have tuning optimism.

## Training CV selection scores

|                     |   mean_training_CV_F1 |
|:--------------------|----------------------:|
| Logistic Regression |              0.709971 |
| Decision Tree       |              0.70399  |
| Random Forest       |              0.764968 |
| Tuned Random Forest |              0.760471 |

## Saved pipeline reload

PASS: joblib reload produces identical predictions on all raw test inputs, including missing ages. The artifact contains the fitted ColumnTransformer and classifier together. Run `python analytics/predict.py` to demonstrate raw-input inference. The artifact is regenerated under runtime/ to avoid committing binary model files.
