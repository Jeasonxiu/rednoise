# Test 6: Posterior predictive checking
import os
from matplotlib import pyplot as plt
from cubetools import get_datacube
from timeseries import TimeSeries
import pickle
import numpy as np
plt.ion()


def rn4(wave, location, derotate=False, Xrange=None, Yrange=None):
    # Main directory where the data is
    maindir = os.path.expanduser(location)
    # Which wavelength to look at

    # Construct the directory
    directory = os.path.join(maindir, wave)

    # Load in the data using a very specific piece of code that will cut down
    # the region quite dramatically
    print('Loading data from ' + directory)

    dc = get_datacube(directory, derotate=derotate)
    # Get some properties of the datacube
    ny = dc.shape[0]
    nx = dc.shape[1]
    if Xrange is None:
        xr = [0, nx - 1]
    else:
        xr = Xrange
    if Yrange is None:
        yr = [0, ny - 1]
    else:
        yr = Yrange

    return dc[yr[0]:yr[1], xr[0]:xr[1], :], directory


def get_pixel_locations(iput=None, nsample=100):
    """
    Define a set of pixel locations or load them in from file.
    """
    # Load the locations, or create them.
    if isinstance(iput, (str, unicode)):
        pixel_locations = pickle.load(open(iput, 'rb'))
    else:
        pixel_locations = zip(np.random.randint(0, high=iput[0], size=nsample),
                              np.random.randint(0, high=iput[1], size=nsample))
         
    return pixel_locations


def get_tslist(dc, pixel_locations, name=''):
    """
    Define time-series from the datacube.
    """
    # Get some properties of the datacube
    nt = dc.shape[2]
    
    # Create the sample time array
    dt = 12.0
    t = dt * np.arange(0, nt)
    
    # Define a list of time-series
    tslist = []
    for pxy in pixel_locations:
        ts = TimeSeries(t, dc[pxy[0], pxy[1]])
        ts.name = name + '(' + str(pxy[0]) + ',' + str(pxy[1]) + ')'
        tslist.append(ts)

    return tslist
