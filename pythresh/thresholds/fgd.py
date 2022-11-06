import numpy as np
from sklearn.utils import check_array
from .base import BaseThresholder
from .thresh_utility import normalize, cut, gen_kde


class FGD(BaseThresholder):
    """FGD class for Fixed Gradient Descent thresholder.

       Use the fixed gradient descent to evaluate a non-parametric means
       to threshold scores generated by the decision_scores where outliers
       are set to any value beyond where the first derivative of the kde
       with respect to the decision scores passes the mean of the first
       and second inflection points. See :cite:`qi2021fgd` for details.

       Parameters
       ----------

       Attributes
       ----------

       thresh_ : threshold value that seperates inliers from outliers

       Notes
       -----

       A probability distribution of the decision scores is generated using
       kernel density estimation. The first derivative of the pdf is
       calculated, and the threshold is set as the middle point between the
       first and second inflection points starting from the left side of the
       data range.

    """

    def __init__(self):

        pass

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

        # Generate KDE
        val, dat_range = gen_kde(decision,0,1,len(decision)*3)

        # Calculate the first derivative of the KDE with respect
        # to the data range
        deriv = np.gradient(val, dat_range[1]-dat_range[0])

        count = 0
        ind = []

        # Find the first two inflection points
        for i in range(len(deriv)-1):

            if (deriv[i]>0)&(deriv[i+1]<=0):
                count+=1
                ind.append(i)
                if count==2:
                    break
        try:
            limit = (dat_range[ind[0]]+dat_range[ind[1]])/2
        except IndexError:
            limit = 1.1
        self.thresh_ = limit

        return cut(decision, limit)
