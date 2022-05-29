import numpy as np
from scipy import ndimage as ndi
from sklearn.utils import check_array
from .base import BaseThresholder
from .thresh_utility import normalize, cut, gen_kde

#https://github.com/scikit-image/scikit-image/blob/v0.19.2/skimage/filters/thresholding.py

def histogram(decision, nbins):
    """Generate histograms and get bin ceneters"""

    counts, bin_edges = np.histogram(decision, bins=nbins, range=(0,1))
    bin_centers = (bin_edges[:-1] + bin_edges[1:])/2.

    return bin_centers, counts

def find_local_maxima_idx(hist):
    """Find the local maxima in histogram"""

    maximum_idxs = list()
    direction = 1

    for i in range(hist.shape[0] - 1):
        if direction > 0:
            if hist[i + 1] < hist[i]:
                direction = -1
                maximum_idxs.append(i)
        else:
            if hist[i + 1] > hist[i]:
                direction = 1

    return maximum_idxs


def OTSU_thres(bin_centers, counts):
    """Otsu's method for histogram based thresholding"""

    counts = counts.astype(float)

    #class probabilities for all possible thresholds
    weight1 = np.cumsum(counts)
    weight2 = np.cumsum(counts[::-1])[::-1]
        
    # class means for all possible thresholds
    mean1 = np.cumsum(counts * bin_centers) / weight1
    mean2 = (np.cumsum((counts * bin_centers)[::-1]) / weight2[::-1])[::-1]

    # Clip ends to align class 1 and class 2 variables:
    variance12 = weight1[:-1] * weight2[1:] * (mean1[:-1] - mean2[1:])**2

    idx = np.argmax(variance12)

    return bin_centers[idx]

def YEN_thres(bin_centers, counts):
    """Yen's method for histogram based thresholding"""

    # Calculate probability mass function
    pmf = counts.astype(np.float32) / counts.sum()
    P1 = np.cumsum(pmf) 
    P1_sq = np.cumsum(pmf ** 2)
        
    # Get cumsum calculated from end of squared array:
    P2_sq = np.cumsum(pmf[::-1] ** 2)[::-1]
        
    # Get critical value
    crit = np.log(((P1_sq[:-1] * P2_sq[1:]) ** -1) *
                    (P1[:-1] * (1.0 - P1[:-1])) ** 2)
    
    return bin_centers[crit.argmax()]

def ISODATA_thres(bin_centers, counts):
    """ISODATA method for histogram based thresholding"""
    
    counts = counts.astype(np.float32)

    # csuml and csumh contain the count of pixels in that bin or lower, and
    # in all bins strictly higher than that bin, respectively
    csuml = np.cumsum(counts)
    csumh = csuml[-1] - csuml

    # intensity_sum contains the total score intensity from each bin
    intensity_sum = counts * bin_centers

    # Get the lower and higher average value of all scoresin that bin or lower, and
    # in all bins strictly higher than that bin, respectively.
    csum_intensity = np.cumsum(intensity_sum)
    lower = csum_intensity[:-1] / csuml[:-1]
    higher = (csum_intensity[-1] - csum_intensity[:-1]) / csumh[:-1]

    # Find threshold values that meet the criterion t = (l + m)/2
    all_mean = (lower + higher) / 2.0
    bin_width = bin_centers[1] - bin_centers[0]

    # Look only at thresholds that are below the actual all_mean value
    distances = all_mean - bin_centers[:-1]
    
    return  bin_centers[:-1][(distances >= 0) & (distances < bin_width)][0]

def LI_thres(decision, bin_centers, counts):
    """Li's iterative Minimum Cross Entropy method for histogram
       based thresholing"""

    counts = counts.astype(float)

    tolerance = np.min(np.diff(np.unique(decision)))/2
    t_next = np.mean(decision) # initial new guess for iteration
    t_curr = -2 * tolerance # initial old guess for iteration

    
    # Iterate until the new and old thresholds difference
    # is less than the tolerance
    while abs(t_next - t_curr)>tolerance:
        
        t_curr = t_next
        outlier = bin_centers>t_curr
        inlier = ~outlier

        mean_out = np.average(bin_centers[outlier],
                                weights=counts[outlier])
        
        mean_in = np.average(bin_centers[inlier],
                                weights=counts[inlier])

        t_next = ((mean_in - mean_out)
                    / (np.log(mean_in) - np.log(mean_out)))
        
    return t_next

def Minimum_thres(bin_centers, counts):
    """Minimum method for histogram based thresholding"""

    smooth_hist = counts.astype(np.float64, copy=False)

    for counter in range(10000):
        smooth_hist = ndi.uniform_filter1d(smooth_hist, 3)
        maximum_idxs = find_local_maxima_idx(smooth_hist)
        if len(maximum_idxs) < 3:
            break

    # Find lowest point between the maxima
    threshold_idx = np.argmin(smooth_hist[maximum_idxs[0]:maximum_idxs[1] + 1])

    return bin_centers[maximum_idxs[0] + threshold_idx]

def Triangle_thres(bin_centers, counts):
    """Triangle algorithm for histogram based thresholding"""

    nbins = len(counts)

    # Find peak, lowest and highest score levels.
    arg_peak_height = np.argmax(counts)
    peak_height = counts[arg_peak_height]
    arg_low_level, arg_high_level = np.where(counts > 0)[0][[0, -1]]

    # Flip is True if left tail is shorter.
    flip = arg_peak_height - arg_low_level < arg_high_level - arg_peak_height
    if flip:
        counts = counts[::-1]
        arg_low_level = nbins - arg_high_level - 1
        arg_peak_height = nbins - arg_peak_height - 1

    # Set up the coordinate system.
    width = arg_peak_height - arg_low_level
    x1 = np.arange(width)
    y1 = counts[x1 + arg_low_level]

    # Normalize.
    norm = np.sqrt(peak_height**2 + width**2)
    peak_height /= norm
    width /= norm

    # Maximize the length.
    length = peak_height * x1 - width * y1
    arg_level = np.argmax(length) + arg_low_level

    if flip:
        arg_level = nbins - arg_level - 1

    return bin_centers[arg_level]
    
   

class HIST(BaseThresholder):
    """HIST class for Histogram based thresholders.

       Use histograms methods as described in scikit-image.filters to
       evaluate a non-parametric means to threshold scores generated by
       the decision_scores where outliers are set by histogram generated
       thresholds depending on the selected methods. 
       
       Paramaters
       ----------
       nbins : number of bins to use in the hostogram
               int, optional (default=None)
               
       method : str, optional (default='otsu')
               {'otsu', 'yen', 'isodata', 'li', 'minimum', 'triangle'}

       Attributes
       ----------

       eval_: numpy array of binary labels of the training data. 0 stands
           for inliers and 1 for outliers/anomalies.

    """

    def __init__(self, method='otsu', nbins=None):

        super(HIST, self).__init__()
        self.nbins = nbins
        self.method = method
        self.method_funcs = {'otsu': OTSU_thres, 'yen': YEN_thres,
                             'isodata': ISODATA_thres, 'li': LI_thres,
                             'minimum': Minimum_thres,
                             'triangle': Triangle_thres}

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

        #  Set adaptive default if bins are None
        if self.nbins is None:
            self.nbins = int(len(decision)*0.7)

        # Generate histogram 
        bin_centers, counts = histogram(decision, self.nbins)

        # Threshold histogram
        if self.method!='li':
            threshold = self.method_funcs[str(self.method)](bin_centers, counts)

        else:
            threshold = self.method_funcs[str(self.method)](decision, bin_centers, counts)

        # Evaluate scores and create labels
        outliers = np.where(decision>threshold)
        scores = np.zeros(len(decision), dtype=int)
        scores[outliers] = 1

        self.thresh_ = threshold
        
        return  scores