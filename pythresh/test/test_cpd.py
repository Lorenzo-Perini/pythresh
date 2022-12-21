# -*- coding: utf-8 -*-
from __future__ import division, print_function

import sys
import unittest
from os.path import dirname as up

# noinspection PyProtectedMember
from numpy.testing import assert_equal
from pyod.models.knn import KNN
from pyod.utils.data import generate_data

from pythresh.thresholds.cpd import CPD

# temporary solution for relative imports in case pythresh is not installed
# if pythresh is installed, no need to use the following line

path = up(up(up(__file__)))
sys.path.append(path)


class TestCPD(unittest.TestCase):
    def setUp(self):
        self.n_train = 200
        self.n_test = 100
        self.contamination = 0.1
        self.X_train, self.X_test, self.y_train, self.y_test = generate_data(
            n_train=self.n_train, n_test=self.n_test,
            contamination=self.contamination, random_state=42)

        self.clf = KNN()
        self.clf.fit(self.X_train)

        self.scores = self.clf.decision_scores_
        self.methods = ['Dynp', 'KernelCPD', 'Binseg', 'BottomUp']
        self.transforms = ['cdf', 'kde']

    def test_prediction_labels(self):

        for method in self.methods:
            for transform in self.transforms:

                self.thres = CPD(method=method, transform=transform)
                pred_labels = self.thres.eval(self.scores)
                assert (self.thres.thresh_ is not None)

                assert_equal(pred_labels.shape, self.y_train.shape)

                assert (pred_labels.min() == 0)
                assert (pred_labels.max() == 1)