import numpy as np
from sklearn.metrics import auc
from sklearn.utils import check_array
from .base import BaseThresholder
from .thresh_utility import normalize, cut, gen_kde


class AUCP(BaseThresholder):
    """AUCP class for Area Under Curve Precentage thresholder.

       Use the area under the curve to evaluate a non-parametric means
       to threshold scores generated by the decision_scores where outliers
       are set to any value beyond where the auc of the kde is less
       than the (median + abs(median-mean)) percent of the total kde auc.
       See :cite:`ren2018aucp` for details
       
       Paramaters
       ----------

       Attributes
       ----------

       thres_ : threshold value that seperates inliers from outliers

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
        val, dat_range = gen_kde(decision,0,1,len(decision)*2)
        val = normalize(val)

        # Get the total area under the curve
        tot_area = auc(dat_range,val)

        # Get area percentage limit
        med = np.median(decision)
        perc = med+abs(med-np.mean(decision))
        

        # Apply the limit to where the area is less than that limit percentage
        # of the total area under the curve
        limit = 1
        for i in range(len(dat_range)):
   
            splt_area = auc(dat_range[i:], val[i:])

            if splt_area<perc*tot_area:
                limit = dat_range[i]
                break

        self.thresh_ = limit
        
        return cut(decision, limit)
