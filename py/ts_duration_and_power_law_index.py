"""
The purpose of this program is analyze test data so we can find out how long
a time series has to be in order for it to have enough information in it that
we are able to determine its power law index a reasonable percentage of the
time.

Ha! Longer time series will lead to more precise determinations of the
power law index, but the proportion lying within the credible interval
should be approximately the same, and in the limit, identical. I think.

"""
 
import numpy as np
import matplotlib.pyplot as plt
import rn_utils
import pymc
import pickle

# Dump plots?
show_plot = False

# Where to dump the data
pickle_directory = '/home/ireland/ts/pickle/'

# Where to put the images
img_directory = '/home/ireland/ts/img/'

# Set up the simulated data
# Initial length of the time series
n_initial = 300

# Sampling (SDO AIA sample rate is once every 12 seconds)
dt = 12.0

# power law index
alpha = 1.0

# The time-series is multiplied by this factor
n_increment = np.sqrt(2.0)

# Maximum number of increments
max_increment = 9

# Number of trial data runs at each time-series length
ntrial = 100

# PyMC variables
iterations = 50000
burn = iterations / 4
thin = 5

# storage array for the credible interval
ci_keep68 = np.zeros((max_increment, ntrial, 2))

# Least squares fit found
lstsqr_fit = np.zeros((max_increment, ntrial, 2))

# Bayesian posterior means
bayes_mean = np.zeros((max_increment, ntrial, 2))

# Storage array for the fraction found
fraction_found = np.zeros((max_increment))

# Storage array for the length of the time-series
nkeep = np.zeros((max_increment))

# String required to save data
alpha_S = str(np.around(alpha, decimals=2))

# Main loop
for i in range(0, max_increment):
    # increase the length of the time series
    n = np.int(np.rint(n_initial * (n_increment ** i)))
    nkeep[i] = n
    print 'Increment counter ', i, max_increment, n

    for j in range(0, ntrial):
        print 'Trial counter ', j, ntrial
        # ensure repeatable random time-series.  We will need this when we
        # come to analyze the same data in different ways
        seed = j + i * ntrial
        test_data = rn_utils.simulated_power_law(n, dt, alpha, seed=seed)

        # get the power spectrum and frequencies we will analyze at
        observed_power_spectrum = (np.absolute(np.fft.fft(test_data))) ** 2
        fftfreq = np.fft.fftfreq(n, dt)
        these_frequencies = fftfreq > 0
        analysis_frequencies = fftfreq[these_frequencies[:-1]]
        analysis_power = observed_power_spectrum[these_frequencies[:-1]]

        # get a simple estimate of the power law index
        estimate = rn_utils.do_simple_fit(analysis_frequencies, analysis_power)
        c_estimate = estimate[0]
        m_estimate = estimate[1]

        # Keep the least squares fit
        lstsqr_fit[i, j, 0] = c_estimate
        lstsqr_fit[i, j, 1] = m_estimate

        # plot the power law spectrum
        power_fit = c_estimate * analysis_frequencies ** (-m_estimate)

        # PyMC definitions
        # Define data and stochastics
        power_law_index = pymc.Uniform('power_law_index',
                                       lower=-1.0,
                                       upper=m_estimate + 2,
                                       doc='power law index')

        power_law_norm = pymc.Uniform('power_law_norm',
                                      lower=c_estimate * 0.01,
                                      upper=c_estimate * 100.0,
                                      doc='power law normalization')

        # Model for the power law spectrum
        @pymc.deterministic(plot=False)
        def power_law_spectrum(p=power_law_index,
                               a=power_law_norm,
                               f=analysis_frequencies):
            """A pure and simple power law model"""
            out = a * (f ** (-p))
            return out

        spectrum = pymc.Exponential('spectrum',
                               beta=1.0 / power_law_spectrum,
                               value=analysis_power,
                               observed=True)

        # MCMC model as a list
        MCMC_list = [power_law_index, power_law_norm, power_law_spectrum, spectrum]

        # Set up the MCMC model
        M1 = pymc.MCMC(MCMC_list)

        # Run the sampler
        M1.sample(iter=iterations, burn=burn, thin=thin, progress_bar=False)

        # Get the power law index and the normalization
        pli = M1.trace("power_law_index")[:]
        m_posterior_mean = np.mean(pli)
        cli = M1.trace("power_law_norm")[:]
        c_posterior_mean = np.mean(cli)

        bayes_mean[i, j, 0] = c_posterior_mean
        bayes_mean[i, j, 1] = m_posterior_mean

        # Get various properties of the power law index marginal distribution
        # and save them
        ci_keep68[i, j, :] = rn_utils.credible_interval(pli, ci=0.68)

        if show_plot:
            # Plots
            # Calculate the actual fit
            bayes_fit = c_posterior_mean * analysis_frequencies ** (-m_posterior_mean)

            # plot the power spectrum, the quick fit, and the Bayesian fit
            plt.figure(1)
            plt.subplot(2, 2, 1)

            m_estimate_S = str(np.around(m_estimate, decimals=2))
            m_posterior_mean_S = str(np.around(m_estimate, decimals=2))
            alpha_CI_S = str(np.around(ci_keep68[i, j, 0], decimals=2)) + '-' + \
            str(np.around(ci_keep68[i, j, 1], decimals=2))

            plt.plot(test_data)
            plt.xlabel('sample number (n=' + str(n) + ')')
            plt.ylabel('simulated emission')
            plt.title(r'Simulated data $\alpha_{true}$=' + alpha_S + ' , seed=' + str(seed))

            plt.subplot(2, 2, 2)
            plt.loglog(analysis_frequencies, analysis_power, label=r'observed power: $\alpha_{true}=$' + alpha_S)
            plt.loglog(analysis_frequencies, power_fit, label=r'$\alpha_{lstsqr}=$' + m_estimate_S)
            plt.loglog(analysis_frequencies, bayes_fit, label=r'$\alpha_{bayes}=$' + m_posterior_mean_S)
            plt.xlabel('frequency')
            plt.ylabel('power')
            plt.title('Data fit with simple single power law')
            plt.legend()

            plt.subplot(2, 2, 3)
            plt.hist(pli, bins=40, label=r'$\alpha_{bayes}$ 68% CI=' + alpha_CI_S)
            plt.title('power law index PDF')
            plt.legend()

            plt.subplot(2, 2, 4)
            plt.hist(cli, bins=40)
            plt.title('power law normalization PDF')

            plt.show()

    # Calculate how often the credible interval includes the true value of the
    # power law index.
    low = np.squeeze(ci_keep68[i, :, 0]) <= alpha
    high = np.squeeze(ci_keep68[i, :, 1]) >= alpha
    fraction_found[i] = np.sum(low * high) / (1.0 * ntrial)
    print fraction_found

# Calculate a filename
filename = "ts_duration_and_power_law_index_" + alpha_S

# Save a plot to file
plt.semilogx(nkeep, fraction_found)
plt.xlabel("length of time series (samples)")
plt.ylabel("fraction found")
plt.savefig(img_directory + filename, format='png')

# Save the data to a pickle file
# Saving the 68% credible intervals, fraction found and length of time series
results = {"low": low, "high": high, "fraction_found": fraction_found,
           "nkeep": nkeep, "alpha": alpha}

pickle.dump(results, open(pickle_directory + filename + '.pickle', "wb"))
