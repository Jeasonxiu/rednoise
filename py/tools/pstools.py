#
# Power spectrum tools
#
import numpy as np
import rnspectralmodels
import study_details

#
# Assume a power law in power spectrum - Use a Bayesian marginal distribution
# to calculate the probability that the power spectrum has a power law index
# 'n'
#
def bayeslogprob(f, I, n, m):
    """
    Return the log of the marginalized Bayesian posterior of an observed
    Fourier power spectra fit with a model spectrum Af^{-n}, where A is a
    normalization constant, f is a normalized frequency, and n is the power law
    index at which the probability is calculated. The marginal probability is
    calculated using a prior p(A) ~ A^{m}.

    The function returns log[p(n)] give.  The most likely value of 'n' is the
    maximum value of p(n).

    f : normalized frequencies
    I : Fourier power spectrum
    n : power law index of the power spectrum
    m : power law index of the prior p(A) ~ A^{m}
    """
    N = len(f)
    term1 = n * np.sum(np.log(f))
    term2 = (N - m - 1) * np.log(np.sum(I * f ** n))
    return term1 - term2


#
# Find the most likely power law index given a prior on the amplitude of the
# power spectrum
#
def most_probable_power_law_index(f, I, m, n):
    blp = np.zeros_like(n)
    for inn, nn in enumerate(n):
        blp[inn] = bayeslogprob(f, I, nn, m)
    return n[np.argmax(blp)]


#
# Implement what to do with the isolated structure limits
#
def structure_location(estimate):
    if estimate > study_details.structure_location_limits['hi']:
        return study_details.structure_location_limits['hi']
    if estimate < study_details.structure_location_limits['lo']:
        return study_details.structure_location_limits['lo']
    return estimate


#
# Generate an initial guess to the log likelihood fit
#
def generate_initial_guess(model_name, finput, p):

    # No initial guess
    initial_guess = None

    # Normalize the input frequency.
    f = finput / finput[0]

    # Generate some initial simple estimates to the power law component
    log_amplitude = np.log(p[0])
    index_estimate = most_probable_power_law_index(f, p, 0.0, np.arange(0.0, 4.0, 0.01))
    log_background = np.log(p[-1])
    background_spectrum = rnspectralmodels.power_law_with_constant([log_amplitude, index_estimate, log_background], f)

    if model_name == 'power law':
        initial_guess = [log_amplitude, index_estimate]

    if model_name == 'power law with constant':
        initial_guess = [log_amplitude, index_estimate, log_background]

    if model_name == 'power law with constant and delta function':

        # Location of the biggest difference between the
        delta_location_index = np.argmax(p - background_spectrum)

        # Make sure the location of the delta function is within required limits
        delta_location = structure_location(f[delta_location_index])

        # Find the nearest index at the position of the delta function
        delta_location_index = np.argmin(np.abs(delta_location - f))

        # Define the estimate of delta function
        log_delta_amplitude = np.log((p - background_spectrum)[delta_location_index])

        # The logarithm of the delta function's location
        log_delta_location = np.log(f[delta_location])

        # Finalize the guess
        initial_guess = [log_amplitude, index_estimate, log_background, log_delta_amplitude, log_delta_location]

    if model_name == 'power law with constant and lognormal':

        # Difference between the data and the model
        diff0 = p - background_spectrum

        # Keep the positive parts only
        positive_index = diff0 > 0.0

        # If there is any positive data
        if len(positive_index) > 0:
            diff1 = diff0[positive_index]
            f1 = f[positive_index]
            # Estimate a Gaussian
            amp = np.log(np.max(diff1))
            pos = np.log(f1[np.argmax(diff1)])
            std = np.std(diff1 * (np.log(diff1) - pos))
            initial_guess = [amp, pos, std]
        else:
            initial_guess = [-100.0,
                             0.5 * (study_details.structure_location_limits['lo'] +
                                    study_details.structure_location_limits['hi']),
                             0.1]


    return initial_guess