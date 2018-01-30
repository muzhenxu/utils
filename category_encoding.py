"""
Use this class to process categorical variables.
document: https://www.slideshare.net/HJvanVeen/feature-engineering-72376750
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
import bisect
from collections import Counter


class labelencoder(LabelEncoder):
    """
    sklearn.preprocess.LabelEncoder can't process values which don't appear in fit label encoder.
    this method can process this problem. Replace all unknown values to a certain value, and encode this
    value to 0.

    Attributes
    ----------
    like sklearn.preprocess.LabelEncoder

    Example
    -------
    enc = labelencoder()
    enc.fit(['a','b','c'])
    enc.transform(['a','v','d'])
    Out: array([1, 0, 0])

    """

    # if don't explicitly specify __init__, class will share it's parent class's __init__ params.
    # def __init__(self):
    #     super(labelencoder, self).__init__()

    def fit(self, X, y=None):
        """
        :param X: array-like of shape (n_samples,)
        :param y: None
        :return:
        """
        l = list(np.unique(X))
        t1 = '<unknown>'
        t2 = -999
        while (t1 in l):
            t1 = t1 + '*'
        while (t2 in l):
            t2 -= t2

        le = LabelEncoder(**self.get_params())
        le.fit(X)

        le_classes = le.classes_.tolist()
        try:
            bisect.insort_left(le_classes, t1)
            self.unknown = t1
        except:
            bisect.insort_left(le_classes, t2)
            self.unknown = t2
        le.classes_ = le_classes
        self.encoder = le

    def transform(self, X):
        """
        :param X: array-like of shape (n_samples,)
        :return:
        """
        X = [s if s in self.encoder.classes_ else self.unknown for s in X]
        return self.encoder.transform(X)


class onehotencoder(OneHotEncoder):
    """
    sklearn.preprocess.OnehotEncoder only can process numerical values.
    this method can process str.

    Attributes
    ----------
    like sklearn.preprocess.OneHotEncoder

    Example
    -------
    enc = onehotencoder(sparse=False)
    enc.fit(['a','b','c'])
    enc.transform(['a','v','d'])
    Out:
    array([[ 1.,  0.,  0.],
       [ 0.,  0.,  0.],
       [ 0.,  0.,  0.]])


    """

    # def __init__(self):
    #     super(onehotencoder, self).__init__()

    def fit(self, X, y=None):
        """
        :param X: array-like of shape (n_samples,)
        :param y: None
        :return:
        """
        le = labelencoder()
        le.fit(X)
        self.le = le

        X = self.le.transform(X)

        # below codes can share the init params, but onehot will be not a instance.so will haven't its attributes.
        # onehot = OneHotEncoder
        # onehot.fit(self, X.reshape(-1, 1))
        # self.encoder.transform(self, X.reshape(-1, 1))

        onehot = OneHotEncoder(**self.get_params())
        onehot.fit(X.reshape(-1, 1))

        self.encoder = onehot

    def transform(self, X):
        """
        :param X: array-like of shape (n_samples,)
        :return:
        """
        X = self.le.transform(X)
        return self.encoder.transform(X.reshape(-1, 1))


class countencoder(object):
    """
    count encoding: Replace categorical variables with count in the train set.
    replace unseen variables with 1.
    Can use log-transform to be avoid to sensitive to outliers.
    Only provide log-transform with base e, because I think it's enough.


    Attributes
    ----------
    dmap: a collections.Counter(which like dict) map variable's values to its frequency.

    Example
    -------
    enc = countencoder()
    enc.fit(['a','b','c', 'b', 'c', 'c'])
    enc.transform(['a','c','b'])
    Out:
    array([ 0.        ,  1.09861229,  0.69314718])

    """

    def __init__(self, unseen_values=1, log_transform=True, smoothing=1):
        self.unseen_values = unseen_values
        self.log_transform = log_transform
        self.smoothing = 1

    def fit(self, X, y=None):
        """
        :param X: array-like of shape (n_samples,)
        :param y: None
        :return:
        """
        self.dmap = Counter(X)

    def transform(self, X):
        """
        :param X: array-like of shape (n_samples,)
        :return:
        """
        # TODO: maybe use pd.Series with replace can faster. should test.
        X = np.array([self.dmap[i] + self.smoothing if i in self.dmap.keys() else self.unseen_values for i in X])
        if self.log_transform:
            X = np.log(X)
        return X


class targetencoder(object):
    """
    this method uses to encode variables by target.
    Only support binary classification and regression.
    Form of stacking: single-variable model which outputs average target.

    use m-estimate to smooth.
    use normal to random value.

    Attributes
    ----------
    dmap: a dict map variables to its average target with smooth and random.
    base_p: target mean

    Example
    -------
    enc = targetencoder()
    enc.fit(np.array(['a','b','c', 'b', 'c', 'c']), np.array([1, 0, 1, 1, 0, 1]))
    enc.transform(np.array(['a','c','b']))
    Out:
    array([ 1.03627629,  0.58939665,  0.55091546])

    """

    def __init__(self, random_noise=0.05, smoothing=0.1, random_seed=10):
        self.random_noise = random_noise
        self.smoothing = smoothing
        self.random_seed = random_seed

    def fit(self, X, y=None):
        # TODO: add if condition to judge X is continous or binary.
        # TODO: Is it necessary to make sure values which add random keep theres order? And does control values less than 1 and more than 0?
        if y is None:
            raise Exception('encoder need valid y label.')

        X = np.array(X)
        y = np.array(y)

        self.classes_ = np.unique(X)
        np.random.seed(self.random_seed)
        self.bias = np.random.normal(0, self.random_noise, len(self.classes_))
        self.dmap = {}
        self.base_p = y.mean()
        for i, key in enumerate(self.classes_):
            l = y[X == key]
            p = (sum(l) + self.smoothing * len(l) * self.base_p) / (len(l) + self.smoothing * len(l))
            p += self.bias[i]
            self.dmap[key] = p

    def transform(self, X):
        X = np.array([self.dmap[i] if i in self.dmap.keys() else self.base_p for i in X])
        return X


# class CategoryEncoder(object):
#     def __init__(self, method='onehotencoder'):
#         self.method = method
#
#     def fit(self, X, y=None):
#         self.enc = eval(self.method)()
#         self.enc.fit(X, y)
#
#     def transform(self, X):
#         return self.enc.transform(X)

def CategoryEncoder(method='countencoder'):
    return eval(method)()


# TODO: hashencoder
# import hashlib
# class HashingEncoder(object):
#     def __init__(self):
#         self.cols_set = []
#         self.unknown_type = None
#
#     def fit(self, X, col=None, n_components=5, hashing_method='md5'):
#         """
#         :param X: array-like of shape (n_samples,)
#         :param y: None
#         :return:
#         """
#         if n_components <= 0:
#             raise ValueError('n_components shout be greater than 0.')
#
#         if not col:
#             col = 'hh'
#         self.col = col
#         self.n_components = n_components
#         self.hashing_method = hashing_method
#
#         self.cols_set = list(np.unique(X))
#         self.unknown_type = '<unknown>'
#         while (self.unknown_type in self.cols_set):
#             self.unknown_type += '*'
#         return self
#
#     def transform(self, X):
#         """
#         :param X: array-like of shape (n_samples,)
#         :return:
#         """
#         X_tmp = [_  if _ in self.cols_set else self.unknown_type  for _ in X]
#         X_tmp = pd.DataFrame(X_tmp, columns=[self.col])
#         return self.__hash_col(X_tmp)
#
#
#     def __hash_col(self, df):
#         """
#         :param df: dataframe of X
#         return:
#         """
#         cols = [f'{self.col}_{i}' for i in range(self.n_components)]
#         def xform(x):
#             tmp = np.zeros(self.n_components)
#             tmp[self.__hash(x) % self.n_components] = 1
#             return pd.Series(tmp, index=cols).astype(int)
#         df[cols] = df[self.col].apply(xform)
#         return df.drop(self.col, axis=1)
#
#     def __hash(self, string):
#         if self.hashing_method == 'md5':
#             return int(hashlib.md5(str(string).encode('utf-8')).hexdigest(), 16)
#         else:
#             raise ValueError('Hashing Method: %s Not Available. Please check that.' % self.hashing_method)


if __name__ == '__main__':
    enc = CategoryEncoder()
    enc.fit(np.array(['a', 'c', 'd', 'a', 'a', 'd']))
    enc.transform(np.array(['f', 'c', 'd']))
