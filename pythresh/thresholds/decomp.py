import numpy as np
from sklearn.decomposition import PCA, NMF
from sklearn.utils import check_array
from .base import BaseThresholder
from .thresh_utility import normalize, cut, gen_cdf


class DECOMP(BaseThresholder):
    """DECOMP class for Decomposition based thresholders.

       Use decomposition to evaluate a non-parametric means
       to threshold scores generated by the decision_scores where outliers
       are set to any value beyond the maximum of the decomposed
       matrix that results from decomposing the cumulative distribution
       function of the decision scores.
       See :cite:`boente2002decomp` for details
       
       Paramaters
       ----------
       
       method: {'NMF', 'PCA'}, optional (default='PCA')
            Method to use for decomposition
        
            - 'NMF':  Non-Negative Matrix Factorization
            - 'PCA':  Principal component analysis

       Attributes
       ----------

       thres_ : threshold value that seperates inliers from outliers

    """

    def __init__(self, method='PCA'):

        self.method = method
        self.method_funcs = {'NMF':NMF(random_state=1234),
                             'PCA':PCA(random_state=1234)}

    def eval(self, decision):
        """Outlier/inlier evaluation process for decision scores.

        Parameters
        ----------
        decision : np.array or list of shape (n_samples)
                   which are the decision scores from a
                   outlier detection.

        Returns
        -------
        outlier_labels : numpy array of shape (n_samples,)
            For each observation, tells whether or not
            it should be considered as an outlier according to the
            fitted model. 0 stands for inliers and 1 for outliers.
        """

        decision = check_array(decision, ensure_2d=False)

        decision = normalize(decision)

        # Generate a CDF of the decision scores
        val, dat_range = gen_cdf(decision,0,1,len(decision)*3)
        val = normalize(val)

        # Apply decomposition
        dec = self.method_funcs[str(self.method)].fit_transform(val.reshape(-1,1))

        # Set limit to max value from decomposition matrix
        limit = np.max(dec)
        if limit>0.5:
            limit = 1-limit
            
        self.thresh_ = limit
        
        return cut(decision, limit)