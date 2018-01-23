# coding=utf-8
import sys
import time
import json
import pandas as pd
import numpy as np
import hyperopt as hpt
from sklearn.model_selection import KFold

import L2DeepSurv, utils

global Logval, eval_cnt, time_start
global train_X, train_y
global hidden_layers

########## Configuration for running hyperparams tuning ##########
# Usage: python HyperParametersTuning.py Layer1 Layer2 Layer3 ...

# Don't change it easily
OPTIMIZER_LIST = ['sgd', 'adam']
ACTIVATION_LIST = ['relu', 'sigmoid', 'tanh']
DECAY_LIST = [1.0, 0.999]

# Change it Before you running
SEED = 40
KFOLD = 4
MAX_EVALS = 40
NUM_EPOCH = 2400

###################################################################

def argsTrans(args):
    params = {}
    params["learning_rate"] = args["learning_rate"] * 0.1 + 0.1
    params["learning_rate_decay"] = DECAY_LIST[args["learning_rate_decay"]]
    params['activation'] = ACTIVATION_LIST[args["activation"]]
    params['optimizer'] = OPTIMIZER_LIST[args["optimizer"]]
    params['L1_reg'] = args["L1_reg"] * 0.0001
    params['L2_reg'] = args["L2_reg"] * 0.0001
    return params

def estimate_time():
    global time_start, eval_cnt

    time_now = time.clock()
    total = (time_now - time_start) / eval_cnt * (MAX_EVALS - eval_cnt)
    th = int(total / 3600)
    tm = int((total - th * 3600) / 60)
    ts = int(total - th * 3600 - tm * 60)
    print('Estimate the remaining time: %dh %dm %ds' % (th, tm, ts))

def trainDeepSurv(args):
    global Logval, eval_cnt, time_start
    global train_X, train_y

    m = train_X.shape[1]
    params = argsTrans(args)
    ci_list = []
    # 5-KFold
    kf = KFold(n_splits=KFOLD, shuffle=True, random_state=SEED)
    for train_index, test_index in kf.split(train_X):
        # Split Data(train : test = 4 : 1)
        X_cross_train, X_cross_test = train_X[train_index], train_X[test_index]
        y_cross_train = {'t' : train_y['t'][train_index], 'e' : train_y['e'][train_index]}
        y_cross_test  = {'t' : train_y['t'][test_index],  'e' : train_y['e'][test_index]}
        # Train Network
        ds = L2DeepSurv.L2DeepSurv(X_cross_train, y_cross_train,
                                   m, hidden_layers, 1,
                                   learning_rate=params['learning_rate'], 
                                   learning_rate_decay=params['learning_rate_decay'],
                                   activation=params['activation'],
                                   optimizer=params['optimizer'],
                                   L1_reg=params['L1_reg'], 
                                   L2_reg=params['L2_reg'], 
                                   dropout_keep_prob=1.0)
        ds.train(num_epoch=NUM_EPOCH)
        # Evaluation Network On Test Set
        ci = ds.eval(X_cross_test, y_cross_test)
        ci_list.append(ci)
        # Close Session of tensorflow
        ds.close()
    # Mean of CI on cross validation set
    ci_mean = sum(ci_list) / KFOLD
    Logval.append({'params': params, 'ci': ci_mean})
    # print remaining time
    eval_cnt += 1
    # if eval_cnt % 10 == 0:
    estimate_time()
    
    return -ci_mean

def wtFile(filename, var):
    with open(filename, 'w') as f:
        json.dump(var, f)

def SearchParams(output_file, max_evals = 100):
    global Logval

    space = {
              "learning_rate": hpt.hp.randint("learning_rate", 15), # [0.1, 1.5] = 0.1 * ([0, 14] + 1)
              "learning_rate_decay": hpt.hp.randint("learning_rate_decay", 2),# [0, 1]
              "activation": hpt.hp.randint("activation", 3), # [0, 1, 2]
              "optimizer": hpt.hp.randint("optimizer", 2), # [0, 1]
              "L1_reg": hpt.hp.randint("L1_reg", 11), # [0.0001, 0.0010] = 0.0001 * [0, 10]
              "L2_reg": hpt.hp.randint("L2_reg", 11)  # [0.0001, 0.0010] = 0.0001 * [0, 10]
            }

    best = hpt.fmin(trainDeepSurv, space, algo = hpt.tpe.suggest, max_evals = max_evals)
    wtFile(output_file, Logval)

    print("best params:", argsTrans(best))
    print("best metrics:", -trainDeepSurv(best))

def main(output_file,
         split = 1.0,
         use_simulated_data=False):
    
    global Logval, eval_cnt, time_start
    global train_X, train_y
    global hidden_layers

    if use_simulated_data:
        train_X, train_y = utils.loadSimulatedData()
    else:
        # load raw data
        train_X, train_y = utils.loadRawData(filename = "data//train_idfs.csv")
        # train_X, train_y = utils.loadData(filename = "data//train_idfs.csv",
        #                                   split=split,
        #                                   Normalize=False)
    Logval = []
    hidden_layers = [int(idx) for idx in sys.argv[1:]]
    eval_cnt = 0
    time_start = time.clock()

    print("Data set for SearchParams: ", len(train_X))
    print("Hidden Layers of Network: ", hidden_layers)

    SearchParams(output_file = output_file, max_evals = MAX_EVALS)

if __name__ == "__main__":
    main(output_file="data//hyperopt_log_simulated_tmp.json",
         split = 1.0,
         use_simulated_data=True)