import numpy as np
import scipy.stats as stats
from sklearn.utils import check_array

from .base import BaseThresholder
from .thresh_utility import cut, normalize


class MCST(BaseThresholder):
    r"""MCST class for Monte Carlo Shapiro Tests thresholder.

       Use uniform random sampling and statistical testing to evaluate a
       non-parametric means to threshold scores generated by the decision_scores
       where outliers are set to any value beyond the minimum value left after
       iterative Shapiro-Wilk tests have occurred. Note** accuracy decreases with
       array size. For good results the should be array<1000. However still this
       threshold method may fail at any array size.
       See :cite:`coin2008mcst` for details.

       Parameters
       ----------

       random_state : int, optional (default=1234)
            Random seed for the uniform distribution. Can also be set to None.

       Attributes
       ----------

       thresh_ : threshold value that separates inliers from outliers

       Notes
       -----

       The Shapiro-Wilk test is a frequentist statistical test for normality.
       It is used to test the null-hypothesis that the decision scores came
       from a normal distribution. This test statistic is defined as:

       .. math::

          W = \frac{\left(\sum_{i=1}^n a_i x_{(i)} \right)^2}{\sum_{i=1}^n \left(x_i - \bar{x} \right)^2} \mathrm{,}

       where :math:`\bar{x}` is the mean of the scores and :math:`x_{(i)}`
       is the ith-smallest number in the sample (kth order statistic). The
       coefficients :math:`a_i` is given by:

       .. math::

          (a_1,...,a_n) = \frac{m^{\top}V^{-1}}{\sqrt{m^{\top}V^{-1}V^{-1}m}} \mathrm{,}

       where the vector :math:`m=\lvert(m_1,...,m_n \rvert)^{\top}` and :math:`V`
       is the covariance matrix of the order statistics.

       The threshold is set by first calculating an initial Shapiro-Wilk test
       p-value on the decision scores. Using Monte Carlo simulations, random values
       between 0-1 are inserted into the normalized decision scores and p-values are
       calculated. if the p-value is higher than the initial p-value, the initial p-value
       is set to this value and the random value is stored. The minimum stored random
       value is set as the threshold as it is the minimum found outlier.

    """

    def __init__(self, random_state=1234):
        self.random_state = random_state

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

        # Get Baseline Shapiro-Wilk test p-value
        p_std = stats.shapiro(decision).pvalue

        # Create random dataset to insert and test p-values
        rnd = stats.uniform.rvs(loc=0, scale=1, size=len(
            decision), random_state=self.random_state)
        rnd = normalize(rnd)
        povr = []

        # Iterate and add a new random variable
        # Perform a Shapiro-Wilk test and see if the new
        # distribution has a lower or higher p-value
        # If higher record these potential outlier values
        for i in range(len(rnd)):

            arr = np.append(decision, rnd[i])
            p_check = stats.shapiro(arr).pvalue

            if p_check > p_std:

                p_std = p_check
                povr.append(rnd[i])

        limit = np.min(povr) if povr else 1.1
        self.thresh_ = limit

        return cut(decision, limit)
