"""
Given a time series, fit the given PyMC model to it
"""
import numpy as np
import pymc
import matplotlib.pyplot as plt

def simple_fit(data, dt):
    power = (np.absolute(np.fft.fft(data))) ** 2
    n = len(data)
    fftfreq = np.fft.fftfreq(n, dt)
    these_frequencies = fftfreq > 0
    obs_freq = fftfreq[these_frequencies[:-1]]
    obs_pwr = power[these_frequencies[:-1]]
    plt.loglog(obs_freq, obs_pwr)
    plt.show()
    c = np.polyfit(np.log(obs_freq), np.log(obs_pwr), 1)
    plt.loglog(obs_freq, np.exp(np.polyval(c, np.log(obs_freq))))

    return c


class tobefit:
    def __init__(self, data, dt):
        self.data = data
        self.dt = dt

        # Fourier power
        self.power = (np.absolute(np.fft.fft(self.data))) ** 2

        # Find the Fourier frequencies
        self.n = len(self.data)
        fftfreq = np.fft.fftfreq(self.n, self.dt)
        these_frequencies = fftfreq > 0

        # get the data at all the frequencies that have an exponential distribution.
        # This means dropping the Nyquist frequency which has a chi-square(1)
        # distribution
        self.obs_freq = fftfreq[these_frequencies[:-1]]
        self.obs_pwr = self.power[these_frequencies[:-1]]


class dopymc:
    def __init__(self, PyMCmodel):
        # Do the PYMC fit
        self.PyMCmodel = PyMCmodel
        self.data = data
        self.dt = dt
        
        # Fourier power
        self.power = (np.absolute(np.fft.fft(self.data))) ** 2
        
        # Find the Fourier frequencies
        self.n = len(self.data)
        fftfreq = np.fft.fftfreq(self.n, self.dt)
        these_frequencies = fftfreq > 0
        
        # get the data at all the frequencies that have an exponential distribution.
        # This means dropping the Nyquist frequency which has a chi-square(1)
        # distribution
        self.obs_freq = fftfreq[these_frequencies[:-1]]
        self.obs_pwr = self.power[these_frequencies[:-1]]
    
        # Set up the MCMC model
        self.PyMCmodel.observed_frequencies = self.obs_freq
        self.PyMCmodel.observed_power = self.obs_pwr
        
        #
        self.M1 = pymc.MCMC(self.PyMCmodel)
