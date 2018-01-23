import numpy as np
import random
import pandas as pd
from sklearn.model_selection import ShuffleSplit

from dataset import SimulatedData

def prepare_data(x, label):
    if isinstance(label, dict):
       e, t = label['e'], label['t']

    # Sort Training Data for Accurate Likelihood
    sort_idx = np.argsort(t)[::-1]
    x = x[sort_idx]
    e = e[sort_idx]
    t = t[sort_idx]

    return x, {'e': e, 't': t}

def parse_data(x, label):
    # sort data by t
    x, label = prepare_data(x, label)
    e, t = label['e'], label['t']

    failures = {}
    atrisk = {}
    n, cnt = 0, 0

    for i in range(len(e)):
        if e[i]:
            if t[i] not in failures:
                failures[t[i]] = [i]
                n += 1
            else:
                # ties occured
                cnt += 1
                failures[t[i]].append(i)

            if t[i] not in atrisk:
                atrisk[t[i]] = []
                for j in range(0, i+1):
                    atrisk[t[i]].append(j)
            else:
                atrisk[t[i]].append(i)
    # when ties occured frequently
    if cnt >= n / 2:
        ties = 'efron'
    elif cnt > 0:
        ties = 'breslow'
    else:
        ties = 'noties'

    return x, e, t, failures, atrisk, ties

def loadSimulatedData(hr_ratio=2000, n=2000, m=10, num_var=2, seed=1):
    data_config = SimulatedData(hr_ratio, num_var = num_var, num_features = m)
    data = data_config.generate_data(n, seed=seed)
    data_X = data['x']
    data_y = {'e': data['e'], 't': data['t']}
    return data_X, data_y

def loadData(filename = "data//surv_aly_idfs.csv", 
             tgt={'e': 'idfs_bin', 't': 'idfs_month'}, 
             split=1.0,
             Normalize=True,
             seed=40):
    data_all = pd.read_csv(filename)

    ID = 'patient_id'
    target = list(tgt.values())
    L = target + [ID]
    x_cols = [x for x in data_all.columns if x not in L]

    X = data_all[x_cols]
    y = data_all[target]
    # Normalized data
    if Normalize:
        for col in X.columns:
            X.loc[:, col] = (X.loc[:, col] - X.loc[:, col].mean()) / (X.loc[:, col].max() - X.loc[:, col].min())
    # Split data
    if split == 1.0:
        train_X, train_y = X, y
    else:
        sss = ShuffleSplit(n_splits = 1, test_size = 1-split, random_state = seed)
        for train_index, test_index in sss.split(X, y):
            train_X, test_X = X.loc[train_index, :], X.loc[test_index, :]
            train_y, test_y = y.loc[train_index, :], y.loc[test_index, :]
    # print information about train data
    print("Number of rows: ", len(train_X))
    print("X cols: ", len(train_X.columns))
    print("Y cols: ", len(train_y.columns))
    print("X.column name:", train_X.columns)
    print("Y.column name:", train_y.columns)
    # Transform type of data to np.array
    train_X = train_X.values.astype(np.float32)
    train_y = {'e': train_y[tgt['e']].values.astype(np.int32),
               't': train_y[tgt['t']].values.astype(np.float32)}
    if split == 1.0:
        return train_X, train_y
    else:
        test_X = test_X.values.astype(np.float32)
        test_y = {'e': test_y[tgt['e']].values.astype(np.int32),
                  't': test_y[tgt['t']].values.astype(np.float32)}
        return train_X, train_y, test_X, test_y

def loadRawData(filename = "data//train_idfs.csv"):
    # Get raw data(no header, no split, has been normalized)
    data_all = pd.read_csv(filename, header=None)

    num_features = len(data_all.columns)

    X = data_all.loc[:, 0:(num_features-3)]
    y = data_all.loc[:, (num_features-2):]
    # print information about data
    print("Number of rows: ", len(X))
    print("X cols: ", len(X.columns))
    print("Y cols: ", len(y.columns))
    # Transform type of data to np.array
    X = X.values.astype(np.float32)
    y = {'e': y.loc[:, (num_features-2)].values.astype(np.int32),
         't': y.loc[:, (num_features-1)].values.astype(np.float32)}

    return X, y