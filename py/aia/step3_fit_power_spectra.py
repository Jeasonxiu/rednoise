#
# USE THIS ONE!
#
#
# Code to fit power laws to some data from the region analysis
#
# Also do posterior predictive checking to find which model fits best.
#
import pickle
import numpy as np
import os
from matplotlib import rc_file
matplotlib_file = '~/ts/rednoise/py/matplotlibrc_paper1.rc'
rc_file(os.path.expanduser(matplotlib_file))
import matplotlib.pyplot as plt

import pymc
from matplotlib.colors import LogNorm
from scipy.optimize import curve_fit

# Normality tests
from scipy.stats import shapiro, anderson
from statsmodels.graphics.gofplots import qqplot

# Distributions that can be fit to the independence coefficient
from scipy.stats import beta as beta_distrib

import aia_specific
import pymcmodels2
import rnspectralmodels
from paper1 import prettyprint, log_10_product, indexplot
from paper1 import csv_timeseries_write, pkl_write, fix_nonfinite, fit_details, get_kde_most_probable
from aia_pymc_pwrlaws_helpers import *

# Reproducible
np.random.seed(1)

plt.ioff()
#
# Set up which data to look at
#
dataroot = '~/Data/AIA/'
ldirroot = '~/ts/pickle_cc_False_dr_False/'
sfigroot = '~/ts/img_cc_False_dr_False/'
scsvroot = '~/ts/csv_cc_False_dr_False/'
corename = 'study2'
sunlocation = 'equatorial'
fits_level = '1.5'
waves = ['193', '171']
regions = ['R6', 'R7']
#regions = ['R3', 'R4', 'R5', 'R6', 'R7']
windows = ['hanning']
manip = 'relative'


neighbour = 'nearest'

"""
#
# Limb
#
dataroot = '~/Data/AIA/'
ldirroot = '~/ts/pickle/'
sfigroot = '~/ts/img_ccmax_mean/'
scsvroot = '~/ts/csv/'
corename = 'shutdownfun6_6hr'
sunlocation = 'limb'
fits_level = '1.0'
waves = ['171']
regions = ['highlimb', 'crosslimb', 'lowlimb', 'moss', 'loopfootpoints1', 'loopfootpoints2']
windows = ['hanning']
manip = 'relative'
"""
#
# Number of posterior predictive samples to calculate
#
# Set to 1 to do a full analytical run.  Set to a high number to do a test
# run
testing = 5

nsample = 5000 / testing

# PyMC control
itera = 100000 / testing
burn = 20000 / testing
thin = 5

# Image file type
imgfiletype = 'pdf'

# Frequency scaling
freqfactor = 1000.0

# Choose to use a prior (or not) for the noise in the power.  When sigma_type
# is set to none, then no prior is used.
sigma_type = {"type": "beta"}
sigma_type = None

# Choose the shape of the bump
bump_shape = 'lognormal'

coherence_wsize = 3


for iwave, wave in enumerate(waves):
    print(' ')
    print('##################################################################')
    prettyprint('Data')
    # Which wavelength?
    print('Wave: ' + wave + ' (%i out of %i)' % (iwave + 1, len(waves)))

    # Now that the loading and saving locations are seot up, proceed with
    # the analysis.
    for iregion, region in enumerate(regions):
        # Which region
        prettyprint('Region')
        print('Region: ' + region + ' (%i out of %i)' % (iregion + 1, len(regions)))

        # Create the branches in order
        branches = [corename, sunlocation, fits_level, wave, region]

        # Set up the roots we are interested in
        roots = {"pickle": ldirroot,
                 "image": sfigroot,
                 "csv": scsvroot}

        # Data and save locations are based here
        locations = aia_specific.save_location_calculator(roots,
                                     branches)

        # set the saving locations
        sfig = locations["image"]
        scsv = locations["csv"]

        # Identifier
        ident = aia_specific.ident_creator(branches)

        # Go through all the windows
        for iwindow, window in enumerate(windows):
            # Which window
            print('Window: ' + window + ' (%i out of %i)' % (iwindow + 1, len(windows)))

            # Update the region identifier
            region_id = '.'.join((ident, window, manip))

            # Create a location to save the figures
            savefig = os.path.join(os.path.expanduser(sfig), window, manip)
            if not(os.path.isdir(savefig)):
                os.makedirs(savefig)
            savefig = os.path.join(savefig, region_id)

            #for obstype in ['.iobs', '.logiobs']:
            for obstype in ['.logiobs']:
                #
                print('Analyzing ' + obstype)
                if obstype == '.iobs':
                    print('Data is lognormally distributed.')
                else:
                    print('Data is normally distributed.')

                # Load the power spectrum
                pkl_location = locations['pickle']
                ifilename = 'OUT.' + region_id + obstype
                pkl_file_location = os.path.join(pkl_location, ifilename + '.pickle')
                print('Loading ' + pkl_file_location)
                pkl_file = open(pkl_file_location, 'rb')
                # Frequencies
                freqs = pickle.load(pkl_file)
                # Number of pixels used to create the average
                npixels = pickle.load(pkl_file)
                # Mean Fourier Power per frequency
                pwr_ff_mean = pickle.load(pkl_file)
                # Fitted Fourier power per frequency
                pwr_ff_fitted = pickle.load(pkl_file)
                # Histogram Peak of the Fourier power per frequency
                pwr_ff_peak = pickle.load(pkl_file)
                pkl_file.close()

                # Load the widths
                ifilename = 'OUT.' + region_id
                pkl_file_location = os.path.join(pkl_location, ifilename + '.distribution_widths.pickle')
                print('Loading ' + pkl_file_location)
                pkl_file = open(pkl_file_location, 'rb')
                # Frequencies
                freqs = pickle.load(pkl_file)
                # Standard deviation of the Fourier power per frequency
                std_dev = pickle.load(pkl_file)
                # Fitted width of the Fourier power per frequency
                fitted_width = pickle.load(pkl_file)
                pkl_file.close()

                # Load the coherence
                ifilename = 'OUT.' + region_id
                pkl_file_location = os.path.join(pkl_location, ifilename + '.coherence.' + str(coherence_wsize) + '.' + neighbour + '.pickle')
                print('Loading ' + pkl_file_location)
                pkl_file = open(pkl_file_location, 'rb')
                freqs = pickle.load(pkl_file)
                coher = pickle.load(pkl_file)
                coher_max = pickle.load(pkl_file)
                coher_mode = pickle.load(pkl_file)
                coher_95_hi = pickle.load(pkl_file)
                coher_mean = pickle.load(pkl_file)
                pkl_file.close()

                # Something wrong with the last coherence - estimate it
                coher_95_hi[-1] = coher_95_hi[-2]
                coher_mean[-1] = coher_mean[-2]

                # Load the correlative measures
                ifilename = 'OUT.' + region_id
                pkl_file_location = os.path.join(pkl_location, ifilename + '.correlative.' + neighbour + '.pickle')
                print('Loading ' + pkl_file_location)
                pkl_file = open(pkl_file_location, 'rb')
                cc0_ds = pickle.load(pkl_file)
                cclag_ds = pickle.load(pkl_file)
                ccmax_ds = pickle.load(pkl_file)
                spearman_ds = pickle.load(pkl_file)
                pkl_file.close()

                # Load the correlative measures 2
                ifilename = 'OUT.' + region_id
                pkl_file_location = os.path.join(pkl_location, ifilename + '.correlative2.' + neighbour + '.npy')
                print('Loading ' + pkl_file_location)
                ccmax = np.load(pkl_file_location)

                # Pick which definition of the power to use
                pwr_ff = pwr_ff_mean

                # Fix any non-finite widths and divide by the number of pixels
                # Note that this should be the effective number of pixels,
                # given that the original pixels are not statistically separate.
                prettyprint('%s: Pixel independence calculation' % (neighbour))
                print 'Number of pixels ', npixels
                #print 'Mode, maximum cross correlation coefficient = %f' % (ccmax_ds.mode)
                #dependence_coefficient = coher_mean
                dependence_coefficient = ccmax_ds.mean
                # Independence coefficient - how independent is one pixel compared
                # to its nearest neighbour?
                # independence_coefficient = 1.0 - 0.5 * (np.abs(ccc0) + np.abs(ccclag))
                #
                # NOTE: The astroML package has a method for sampling from an
                # empirical (1-d) distribution.  See http://www.astroml.org/book_figures/chapter3/fig_clone_distribution.html
                # or use the following code snippet:
                # from astroML.density_estimation import EmpiricalDistribution
                # # generate an 'observed' bimodal distribution with 10000 values
                # dists = (stats.norm(-1.3, 0.5), stats.norm(1.3, 0.5))
                # fracs = (0.6, 0.4)
                # x = np.hstack((d.rvs(f * Ndata) for d, f in zip(dists, fracs)))
                # # We can clone the distribution easily with this function
                # x_cloned = EmpiricalDistribution(x).rvs(Nclone)
                #
                # Could use this to sample from the empirical distribution of
                # the independence distribution.  Hmmm - would this work with
                # PyMC?
                #
                #independence_coefficient = 1.0 - np.abs(ccc0)

                #qqq = scipy.stats.beta.fit(cclag)
                #pdf = scipy.stats.beta.pdf(cclag_ds.x, qqq[0], qqq[1])
                #plt.plot(cclag_ds.x, pdf)
                #plt.plot(cclag_ds.xhist[0:-1], ccc_bins * cclag_ds.hist / np.float(np.sum(cclag_ds.hist)))
                #plt.show()

                # Use the coherence estimate to get a frequency-dependent
                # independence coefficient
                # independence_coefficient = 1.0 - coher
                independence_coefficient = 1.0 - np.abs(dependence_coefficient)
                print 'Average independence coefficient ', np.mean(independence_coefficient)
                npixels_effective = independence_coefficient * (npixels - 1) + 1
                #npixels_effective = get_kde_most_probable(ccmax, npixels)
                print("Average effective number of independent observations = %f " % (np.mean(npixels_effective)))
                print npixels_effective
                sigma_of_distribution = fix_nonfinite(std_dev)
                sigma_for_mean = sigma_of_distribution / np.sqrt(npixels_effective)

                if sigma_type is not None:
                    # Fit the independence coefficient with a beta distribution
                    if sigma_type["type"] == 'beta':
                        # Create a PDF from the independence coefficient
                        ic_pdf = (independence_coefficient.size - 1) * independence_coefficient / np.sum(independence_coefficient)
                        ic_fit_params = beta_distrib.fit(ic_pdf)
                        sigma_type = {"type": "beta",
                                      "alpha": ic_fit_params[0],
                                      "beta": ic_fit_params[1],
                                      "npixels": npixels}
                    # Assume a Jeffreys' prior for the scale parameter
                    if sigma_type["type"] == 'jeffreys':
                        sigma_type = {"type": "jeffreys",
                                      "npixels": npixels}

                # Frequency-dependent independence coefficient
                #independence_coefficient = 1.0 - np.abs(ccc0)
                #print 'Coherence: Average independence coefficient ', np.mean(independence_coefficient)
                #npixels_effective = independence_coefficient * (npixels - 1) + 1
                #print("Coherence: Effective number of independent observations = %f " % (np.mean(npixels_effective)))
                #sigma_for_mean = sigma_of_distribution / np.sqrt(npixels_effective)
                #unbiased_factor = np.sqrt(npixels_effective / (npixels_effective ** 2 - npixels_effective))
                #print("Unbiased factor = %f" % (unbiased_factor))
                #sigma = unbiased_factor * fix_nonfinite(sigma)

                # Some models fitting use tau instead of sigma
                #tau = 1.0 / (sigma ** 2)

                # Normalize the frequency
                xnorm = freqs[0]
                normed_freqs = freqs / xnorm
                nfreq = freqs.size

                #
                # Model 0 - the power law
                #
                # Two passes - first pass to get an initial estimate of the
                # spectrum, and a second to get a better estimate using the
                # sigma mean
                prettyprint('Model fitting and results')
                for jjj, sigma in enumerate((sigma_of_distribution, sigma_for_mean)):
                    tau = 1.0 / (sigma ** 2)
                    pwr = pwr_ff
                    if jjj == 0:
                        pymcmodel0 = pymcmodels2.Log_splwc(normed_freqs, pwr, sigma)
                    else:
                        pymcmodel0 = pymcmodels2.Log_splwc(normed_freqs, pwr, sigma, init=A0)
                    passnumber = str(jjj)

                    # Initiate the sampler
                    dbname0 = os.path.join(pkl_location, 'MCMC.M0.' + passnumber + region_id + obstype)
                    M0 = pymc.MCMC(pymcmodel0, db='pickle', dbname=dbname0)

                    # Run the sampler
                    print('M0 : pass %i : Running simple power law model' % (jjj + 1))
                    M0.sample(iter=itera, burn=burn, thin=thin, progress_bar=True)
                    M0.db.close()

                    # Now run the MAP
                    map_M0 = pymc.MAP(pymcmodel0)
                    print(' ')
                    print('M0 : pass %i : fitting to find the maximum likelihood' % (jjj + 1))
                    map_M0.fit(method='fmin_powell')

                    # Get the variables and the best fit
                    A0 = get_variables_M0(map_M0)
                    M0_bf = get_spectrum_M0(normed_freqs, A0)

                    # Plot the traces
                    write_plots(M0, region_id, obstype, savefig, 'M0', passnumber, bins=40, extra_factors=[xnorm])

                    # Get the likelihood at the maximum
                    #likelihood0_data = map_M0.logp_at_max
                    l0_data = get_likelihood_M0(map_M0, normed_freqs, pwr, sigma, obstype)
                    l0_data_logp = get_log_likelihood(pwr, M0_bf, sigma)

                    # Get the chi-squared value
                    chi0 = get_chi_M0(map_M0, normed_freqs, pwr, sigma)
                    print('M0 : pass %i : reduced chi-squared = %f' % (jjj + 1, chi0))
                    print('   : variables ', A0)
                    print('   : estimate log likelihood = %f' % (l0_data_logp))

                #
                # Get an estimate of where the Gaussian bump might be for the
                # second model
                #
                # Frequency range we will consider for the bump
                physical_bump_frequency_limits = np.asarray([1.0 / 10000.0, 1.0 / 100.0])
                bump_frequency_limits = physical_bump_frequency_limits / xnorm
                log_bump_frequency_limits = np.log(bump_frequency_limits)

                where_we_want_to_examine = np.asarray([1.0 / 1000.0, 1.0 / 100.0]) / xnorm
                wwwte_loc_lo = normed_freqs >= where_we_want_to_examine[0]
                wwwte_loc_hi = normed_freqs <= where_we_want_to_examine[1]
                # Get where there is excess unexplained power
                positive_difference = pwr - M0_bf > 0
                # Combine all the conditions to get where the bump might be
                bump_loc = positive_difference * wwwte_loc_lo * wwwte_loc_hi

                # If there are sufficient points, get an estimate of the bump
                if bump_loc.sum() >= 10:
                    x_bump_estimate = normed_freqs[bump_loc]
                    y_bump_estimate = (pwr - M0_bf)[bump_loc]
                    if bump_shape == 'lognormal':
                        try:
                            g_estimate, _ = curve_fit(rnspectralmodels.NormalBump2_CF, np.log(x_bump_estimate), y_bump_estimate)
                        except:
                            g_estimate = [np.mean(y_bump_estimate),
                                          np.sum(np.log(x_bump_estimate) * y_bump_estimate)/np.sum(y_bump_estimate),
                                          np.std(np.log(x_bump_estimate) * y_bump_estimate)]
                    if bump_shape == 'normal':
                        p0_bump_estimate = [np.log(np.max(y_bump_estimate)), np.log(x_bump_estimate[np.argmax(y_bump_estimate)]), 0.0]
                        g_estimate, _ = curve_fit(rnspectralmodels.NormalBump2_allexp_CF, x_bump_estimate, y_bump_estimate, p0=p0_bump_estimate)
                    if g_estimate[0] > pymcmodels2.glimits['gaussian_amplitude'][1]:
                        g_estimate[0] = pymcmodels2.glimits['gaussian_amplitude'][1] - 0.000001
                    A1_estimate = [A0[0], A0[1], A0[2], g_estimate[0], g_estimate[1], g_estimate[2]]
                else:
                    A1_estimate = None
                print "Fitting bump with " + bump_shape
                print "Second model estimate : ", A1_estimate
                print "Physical bump frequency position limits : ", physical_bump_frequency_limits
                print "Normalized log bump frequency limits : ", log_bump_frequency_limits

                #
                # Second model - power law with Gaussian bumps
                #
                for jjj, sigma in enumerate((sigma_of_distribution, sigma_for_mean)):
                    tau = 1.0 / (sigma ** 2)
                    pwr = pwr_ff
                    if jjj == 0:
                        if bump_shape == 'lognormal':
                            pymcmodel1 = pymcmodels2.Log_splwc_AddLognormalBump2(normed_freqs, pwr, sigma, init=A1_estimate, log_bump_frequency_limits=log_bump_frequency_limits)
                            if A1_estimate[4] < log_bump_frequency_limits[0]:
                                A1_estimate[4] = log_bump_frequency_limits[0]
                                print '!! Estimate fit exceeded lower limit of log_bump_frequency_limits. Resetting to limit'
                            if A1_estimate[4] > log_bump_frequency_limits[1]:
                                A1_estimate[4] = log_bump_frequency_limits[1]
                                print '!! Estimate fit exceeded upper limit of log_bump_frequency_limits. Resetting to limit'
                        if bump_shape == 'normal':
                            pymcmodel1 = pymcmodels2.Log_splwc_AddNormalBump2_allexp(normed_freqs, pwr, sigma, init=A1_estimate, normalized_bump_frequency_limits=log_bump_frequency_limits)
                    else:
                        if A1[4] < log_bump_frequency_limits[0]:
                            A1[4] = log_bump_frequency_limits[0]
                            print 'First pass fit exceeded lower limit of log_bump_frequency_limits'
                        if A1[4] > log_bump_frequency_limits[1]:
                            A1[4] = log_bump_frequency_limits[1]
                            print 'First pass fit exceeded upper limit of log_bump_frequency_limits'
                        if bump_shape == 'lognormal':
                            pymcmodel1 = pymcmodels2.Log_splwc_AddLognormalBump2(normed_freqs, pwr, sigma, init=A1, log_bump_frequency_limits=log_bump_frequency_limits)
                        if bump_shape == 'normal':
                            pymcmodel1 = pymcmodels2.Log_splwc_AddNormalBump2_allexp(normed_freqs, pwr, sigma, init=A1, normalized_bump_frequency_limits=log_bump_frequency_limits)

                    # Define the pass number
                    passnumber = str(jjj)

                    # Initiate the sampler
                    dbname1 = os.path.join(pkl_location, 'MCMC.M1.' + passnumber + region_id + obstype)
                    M1 = pymc.MCMC(pymcmodel1, db='pickle', dbname=dbname1)

                    # Run the sampler
                    print('M1 : pass %i : Running power law plus bump model' % (jjj + 1))
                    M1.sample(iter=itera, burn=burn, thin=thin, progress_bar=True)
                    M1.db.close()

                    # Now run the MAP
                    map_M1 = pymc.MAP(pymcmodel1)
                    print(' ')
                    print('M1 : pass %i : fitting to find the maximum likelihood' % (jjj + 1))
                    map_M1.fit(method='fmin_powell')

                    # Get the variables and the best fit
                    A1 = get_variables_M1(map_M1)
                    M1_bf = get_spectrum_M1(normed_freqs, A1, bump_shape)

                    # Plot the traces
                    write_plots(M1, region_id, obstype, savefig, 'M1', passnumber, bins=40, extra_factors=[xnorm])

                    # Get the likelihood at the maximum
                    #likelihood1_data = map_M1.logp_at_max
                    l1_data = get_likelihood_M1(map_M1, normed_freqs, pwr, sigma, bump_shape)
                    l1_data_logp = get_log_likelihood(pwr, M1_bf, sigma)

                    # Get the chi-squared value
                    chi1 = get_chi_M1(map_M1, normed_freqs, pwr, sigma, bump_shape)
                    print('M1 : pass %i : reduced chi-squared = %f' % (jjj + 1, chi1))
                    print('   : variables ', A1)
                    print('   : estimate log likelihood = %f' % (l1_data_logp))

                # Store these results
                fitsummarydata = FitSummary(map_M0, l0_data, chi0, map_M1, l1_data, chi1)

                # Print out these results
                print ' '
                print('M0 likelihood = %f, M1 likelihood = %f' % (fitsummarydata["M0"]["maxlogp"], fitsummarydata["M1"]["maxlogp"]))
                print('M0 likelihood (explicit calculation) = %f, M1 likelihood (explicit calculation) = %f' % (l0_data_logp, l1_data_logp))
                print 'T_lrt for the initial data = %f' % (fitsummarydata["t_lrt"])
                print 'T_lrt for the initial data (explicit calculation) = %f' % (T_LRT(l0_data_logp, l1_data_logp))
                print 'AIC_{0} - AIC_{1} = %f' % (fitsummarydata["dAIC"])
                print 'BIC_{0} - BIC_{1} = %f' % (fitsummarydata["dBIC"])
                print 'M0: chi-squared = %f' % (fitsummarydata["M0"]["chi2"])
                print 'M1: chi-squared = %f' % (fitsummarydata["M1"]["chi2"])

                # Calculate the best fit bump contribution
                if bump_shape == 'lognormal':
                    normalbump_BF = np.log(rnspectralmodels.NormalBump2_CF(np.log(normed_freqs), A1[3], A1[4], A1[5]))
                if bump_shape == 'normal':
                    normalbump_BF = np.log(rnspectralmodels.NormalBump2_allexp_CF(normed_freqs, A1[3], A1[4], A1[5]))
                # Calculate the best fit power law contribution
                powerlaw_BF = np.log(rnspectralmodels.power_law_with_constant(normed_freqs, A1[0:3]))

                # Calculate the posterior mean bump contribution
                ntrace = M1.trace('background')[:].shape[0]
                normalbump_PM = np.zeros(nfreq)
                for i in range(0, ntrace):
                    normalbump_PM = normalbump_PM + np.log(rnspectralmodels.NormalBump2_CF(np.log(normed_freqs),
                                                                                           M1.trace('gaussian_amplitude')[i],
                                                                                           M1.trace('gaussian_position')[i],
                                                                                           M1.trace('gaussian_width')[i]))
                normalbump_PM = normalbump_PM / (1.0 * ntrace)

                # Calculate the posterior mean power law contribution
                powerlaw_PM = np.zeros(nfreq)
                for i in range(0, ntrace):
                    powerlaw_PM = powerlaw_PM + np.log(rnspectralmodels.power_law_with_constant(normed_freqs, [M1.trace('power_law_norm')[i],
                                                                                                               M1.trace('power_law_index')[i],
                                                                                                               M1.trace('background')[i]]))
                powerlaw_PM = powerlaw_PM / (1.0 * ntrace)

                # Print the maximum of the ratio of the bump contribution and
                # to the power law, and the frequency at which occurs
                #bump_to_pl_ratio = np.exp(normalbump_BF) / np.exp(powerlaw_BF)
                bump_to_pl_ratio = np.exp(normalbump_PM) / np.exp(powerlaw_PM)
                max_bump_to_pl_ratio_index = np.argmax(bump_to_pl_ratio)
                print '++++++++++++++++++++++++'
                print 'Maximum bump to PL ratio is %f at frequency = %f mHz' % (bump_to_pl_ratio[max_bump_to_pl_ratio_index], 1000 * freqs[max_bump_to_pl_ratio_index])
                print '++++++++++++++++++++++++'

                # Plot
                title = 'AIA ' + wave + " : " + region
                xvalue = freqfactor * freqs
                fivemin = freqfactor * 1.0 / 300.0
                threemin = freqfactor * 1.0 / 180.0

                # -------------------------------------------------------------
                # Plot the data and the model fits
                model_selector_format = '%i'
                dAIC_value = model_selector_format % (fitsummarydata["dAIC"])
                dAIC_value_string = '$AIC_{1} - AIC_{2} = ' + dAIC_value + '$'
                dBIC_value = model_selector_format % (fitsummarydata["dBIC"])
                dBIC_value_string = '$BIC_{1} - BIC_{2} = ' + dBIC_value + '$'
                ax = plt.subplot(111)

                # Set the scale type on each axis
                ax.set_xscale('log')
                ax.set_yscale('log')

                # Set the formatting of the tick labels
                xformatter = plt.FuncFormatter(log_10_product)
                ax.xaxis.set_major_formatter(xformatter)

                bump_ratio = r'$M_{2}$, $\arg \max[G(\nu)/P_{1}(\nu)]$'

                if region == indexplot["region"] and wave == indexplot["wave"]:
                    labels = {"pwr_ff": 'average Fourier power spectrum',
                              "M0_mean": '$M_{1}$: posterior mean',
                              "M1_mean": '$M_{2}$: posterior mean',
                              "M1_P1": r'posterior mean $P_{1}(\nu)$ component for $M_{2}$',
                              "M1_G": r'posterior mean $G(\nu)$ component for $M_{2}$',
                              'M1: 95% low': r'$M_{1}$: 95% credible interval',
                              "5 minutes": '5 minutes',
                              "3 minutes": '3 minutes',
                              "bump_ratio": bump_ratio}
                else:
                    labels = {"pwr_ff": None,
                              "M0_mean": None,
                              "M1_mean": None,
                              "M1_P1": None,
                              "M1_G": None,
                              'M1: 95% low': None,
                              "5 minutes": None,
                              "3 minutes": None,
                              "bump_ratio": None}

                ax.plot(xvalue, np.exp(pwr_ff), label=labels["pwr_ff"], color='k')

                # Plot the M0 fit
                chired = '\chi^{2}_{red}'
                chiformat = '%4.2f'
                chivalue = chiformat % (fitsummarydata["M0"]["chi2"])
                chivaluestring = '$' + chired + '=' + chivalue + '$'
                #label = '$M_{1}$: maximum likelihood fit, ' + chivaluestring
                #label = '$M_{1}$, maximum likelihood fit'
                #ax.plot(xvalue, np.exp(M0_bf), label=label, color='b')
                ax.plot(xvalue, np.exp(M0.stats()['fourier_power_spectrum']['mean']), label=labels["M0_mean"], color = 'b')
                #plt.plot(xvalue, M0.stats()['fourier_power_spectrum']['95% HPD interval'][:, 0], label='M0: 95% low', color = 'b', linestyle='-.')
                #plt.plot(xvalue, M0.stats()['fourier_power_spectrum']['95% HPD interval'][:, 1], label='M0: 95% high', color = 'b', linestyle='--')

                # Plot the M1 fit
                chivalue = chiformat % (fitsummarydata["M1"]["chi2"])
                chivaluestring = '$' + chired + '=' + chivalue + '$'
                #label = '$M_{2}$: maximum likelihood fit, ' + chivaluestring
                #label = '$M_{2}$, maximum likelihood fit'
                #ax.plot(xvalue, np.exp(M1_bf), label=label, color='r')
                ax.plot(xvalue, np.exp(M1.stats()['fourier_power_spectrum']['mean']), label=labels["M1_mean"], color = 'r')
                #plt.plot(xvalue, np.exp(M1.stats()['fourier_power_spectrum']['95% HPD interval'][:, 0]), label=labels['M1: 95% low'], color = 'r', linestyle='--')
                #plt.plot(xvalue, np.exp(M1.stats()['fourier_power_spectrum']['95% HPD interval'][:, 1]), color = 'r', linestyle='--')

                # Plot each component of M1
                ax.plot(xvalue, np.exp(powerlaw_PM), label=labels["M1_P1"], color='g')
                ax.plot(xvalue, np.exp(normalbump_PM), label=labels["M1_G"], color='g', linestyle='--')
                #ax.plot(xvalue, np.exp(powerlaw_BF), label='power law component of the maximum likelihood fit, $M_{2}$', color='g')
                #ax.plot(xvalue, np.exp(normalbump_BF), label='Gaussian component of the maximum likelihood fit, $M_{2}$', color='g', linestyle='--')

                # Plot the 3 and 5 minute frequencies
                ax.axvline(fivemin, label=labels['5 minutes'], linestyle='--', color='k')
                ax.axvline(threemin, label=labels['3 minutes'], linestyle='-.', color='k')

                # Plot the location of the maximum bump ratio
                ax.axvline(freqfactor * freqs[max_bump_to_pl_ratio_index],
                           label=labels["bump_ratio"],
                           linestyle=':', color='g')

                # Plot the bump limits
                #plt.axvline(np.log10(physical_bump_frequency_limits[0]), label='bump center position limit', linestyle=':' ,color='k')
                #plt.axvline(np.log10(physical_bump_frequency_limits[1]), linestyle=':' ,color='k')

                # Plot the fitness coefficients
                # Plot the fitness criteria - should really put this in a separate function
                xpos = freqfactor * (0.015 * (10.0 ** -3.0))
                #ypos = np.zeros(2)
                #ypos_max = np.log(fit_details()['ylim'][1]) - 1.0
                #ypos_min = np.log(fit_details()['ylim'][0]) + 1.0
                #yrange = ypos_max - ypos_min
                #for yyy in range(0, ypos.size):
                #    ypos[yyy] = np.exp(ypos_min + yyy * yrange / (1.0 * (np.size(ypos) - 1.0)))
                plt.text(xpos, 10.0 ** -3.8, dAIC_value_string)
                #plt.text(xpos, 10.0 ** -4.5, dBIC_value_string)
                #plt.text(xpos, ypos[2], '$T_{LRT}$ = %f' % (fitsummarydata["t_lrt"]))

                chi_M0_string = '%0.2f' % (fitsummarydata["M0"]["chi2"])
                chi_M1_string = '%0.2f' % (fitsummarydata["M1"]["chi2"])
                plt.text(xpos, 10.0 ** -4.3, '$M_{1}$: $\chi^{2}_{r} = ' + chi_M0_string + '$')
                plt.text(xpos, 10.0 ** -4.8, '$M_{2}$: $\chi^{2}_{r} = ' + chi_M1_string + '$')

                # Complete the plot and save it
                if region == indexplot["region"] and wave == indexplot["wave"]:
                    plt.legend(fontsize=10, labelspacing=0.2, loc=1)
                plt.xlabel(r'frequency $\nu$ (mHz)')
                plt.ylabel('power (arb. units)')
                plt.title(title)
                ymin_plotted = np.exp(np.asarray([np.min(pwr_ff) - 1.0,
                                           np.max(normalbump_BF) - 2.0]))
                plt.ylim(fit_details()['ylim'][0], fit_details()['ylim'][1])
                #plt.savefig(savefig + obstype + '.' + passnumber + '.model_fit_compare.pymc.%s' % (imgfiletype))
                plt.savefig(savefig + obstype + '.' + passnumber + '.model_fit_compare.pymc.png')
                plt.close('all')

                f = open(savefig + obstype + '.' + passnumber + '.bump_ratio.pymc.txt', 'w')
                f.write('Maximum bump ratio = %f ' % (bump_to_pl_ratio[max_bump_to_pl_ratio_index]) + '\n')
                f.write('Maximum bump ratio location (mHz) = %f ' % (freqfactor * freqs[max_bump_to_pl_ratio_index]) + '\n')
                f.close()

                # -------------------------------------------------------------
                # Measures of the residuals
                plt.figure(2)
                plt.plot(xvalue, pwr_ff - M0_bf, label='data - M0')
                plt.plot(xvalue, pwr_ff - M1_bf, label='data - M1')
                plt.plot(xvalue, np.abs(pwr_ff - M0_bf), label='|data - M0|')
                plt.plot(xvalue, np.abs(pwr_ff - M1_bf), label='|data - M1|')
                plt.plot(xvalue, sigma_of_distribution, label='estimated log(power) distribution width')
                plt.plot(xvalue, sigma_for_mean, label='estimated error in mean')
                plt.axhline(0.0, color='k')

                # Plot the 3 and 5 minute frequencies
                plt.axvline(fivemin, label='5 mins.', linestyle='--', color='k')
                plt.axvline(threemin, label='3 mins.', linestyle='-.', color='k' )

                # Plot the bump limits
                plt.axvline(np.log10(physical_bump_frequency_limits[0]), label='bump center position limit', linestyle=':' ,color='k')
                plt.axvline(np.log10(physical_bump_frequency_limits[1]), linestyle=':' ,color='k')

                # Complete the plot and save it
                plt.legend(fontsize=10)
                plt.xlabel('log10(frequency (Hz))')
                plt.ylabel('fit residuals')
                plt.title(title)
                plt.savefig(savefig + obstype + '.' + passnumber + '.model_fit_residuals.pymc.png')
                plt.close('all')

                # -------------------------------------------------------------
                # Power ratio
                plt.figure(2)
                plt.semilogy(xvalue, np.exp(normalbump_BF) / np.exp(powerlaw_BF), label='M1[normal bump] / M1[power law]')
                plt.semilogy(xvalue, np.exp(pwr_ff) / np.exp(M1_bf), label='data / M1 best fit')
                plt.semilogy(xvalue, np.exp(pwr_ff) / np.exp(normalbump_BF), label='data / M1[normal bump]')
                plt.semilogy(xvalue, np.exp(pwr_ff) / np.exp(powerlaw_BF), label='data / M1[power law]')
                plt.axhline(1.0, color='k')
                plt.ylim(0.01, 100.0)

                # Plot the 3 and 5 minute frequencies
                plt.axvline(fivemin, label='5 mins.', linestyle='--', color='k')
                plt.axvline(threemin, label='3 mins.', linestyle='-.', color='k')

                # Plot the bump limits
                plt.axvline(np.log10(physical_bump_frequency_limits[0]), label='bump center position limit', linestyle=':' ,color='k')
                plt.axvline(np.log10(physical_bump_frequency_limits[1]), linestyle=':' ,color='k')

                # Complete the plot
                plt.xlabel('log10(frequency (Hz))')
                plt.ylabel('ratio')
                plt.legend(framealpha=0.5, fontsize=8)
                plt.title(title)
                plt.savefig(savefig + obstype + '.' + passnumber + '.model_fit_ratios.pymc.png')
                plt.close('all')

                #--------------------------------------------------------------
                # Residuals / estimated noise - these are the contributions to
                # chi-squared.  Also calculate the Shapiro-Wilks test and the
                # Anderson-Darling test for normality of the M1_bf residuals.
                # These will let us know if the reduced chi-squared values
                # are OK to use.
                M1_residuals = pwr_ff - M1_bf
                nmzd = M1_residuals / sigma_for_mean
                anderson_result = anderson(nmzd, dist='norm')
                ad_crit = anderson_result[1]
                ad_sig = anderson_result[2]
                for jjj in range(0, 5):
                    if anderson_result[0] >= ad_crit[jjj]:
                        anderson_level = ad_sig[jjj]

                shapiro_result = shapiro(nmzd)
                plt.figure(2)
                plt.semilogx(xvalue, (pwr_ff - M0_bf) / sigma_for_mean, label='(data - M0) / sigma for mean')
                plt.semilogx(xvalue, nmzd, label='(data - M1) / sigma for mean')
                plt.axhline(0.0, color='k')

                # Print the normality tests to the plot
                plt.text(xvalue[0], 0.01, 'M1: Shapiro-Wilks p=%f' % (shapiro_result[1]))
                plt.text(xvalue[0], 0.10, 'M1: Anderson-Darling: reject above %s %% (AD=%f)' % (str(anderson_level), anderson_result[0]))

                # Plot the 3 and 5 minute frequencies
                plt.axvline(fivemin, label='5 mins.', linestyle='--', color='k')
                plt.axvline(threemin, label='3 mins.', linestyle='-.', color='k')

                # Plot the bump limits
                plt.axvline(physical_bump_frequency_limits[0], label='bump center position limit', linestyle=':' ,color='k')
                plt.axvline(physical_bump_frequency_limits[1], linestyle=':' ,color='k')

                # Complete the plot and save it
                plt.legend(framealpha=0.5, fontsize=8)
                plt.xlabel('log10(frequency (Hz))')
                plt.ylabel('scaled residual')
                plt.title(title)
                plt.savefig(savefig + obstype + '.' + passnumber + '.scaled_residual.png')
                plt.close('all')

                #--------------------------------------------------------------
                # Size of the residual compared to estimate noise levels
                plt.figure(2)
                plt.semilogx(xvalue, np.abs(nmzd), label='|data - M1| / sigma for mean')
                plt.axhline(1.0, label='expected by normality', color='r')

                # Plot the bump limits
                plt.axvline(physical_bump_frequency_limits[0], label='bump center position limit', linestyle=':' ,color='k')
                plt.axvline(physical_bump_frequency_limits[1], linestyle=':' ,color='k')

                # Complete the plot and save it
                plt.legend(framealpha=0.5, fontsize=8)
                plt.xlabel('log10(frequency (Hz))')
                plt.ylabel('scaled |residual|')
                plt.title(title)
                plt.savefig(savefig + obstype + '.' + passnumber + '.scaled_abs_residual.png')
                plt.close('all')

                #--------------------------------------------------------------
                # qq-plot
                qqplot(nmzd.flatten(), line='45', fit=True)
                plt.savefig(savefig + obstype + '.' + passnumber + '.qqplot.png')
                plt.close('all')

                ###############################################################
                # Save the model fitting information
                pkl_write(pkl_location,
                      'M0_maximum_likelihood.' + region_id + '.pickle',
                      (A0, fitsummarydata, pwr, sigma, M0_bf))

                pkl_write(pkl_location,
                      'M1_maximum_likelihood.' + region_id + '.pickle',
                      (A1, fitsummarydata, pwr, sigma, M1_bf))

                # M1 residuals - saved as CSV so they can be used by other
                # analysis environments
                csv_timeseries_write(os.path.join(os.path.expanduser(scsv)),
                                     '.'.join((ident, 'M1_residuals.csv')),
                                     (freqs, M1_residuals))

                # M1 estimated deviance- saved as CSV so they can be used by
                # other analysis environments
                csv_timeseries_write(os.path.join(os.path.expanduser(scsv)),
                                     '.'.join((ident, 'sigma_for_mean.csv')),
                                     (freqs, sigma_for_mean))

