"""
Step 2
Create power spectra and other summary statistics of the time-series at each
pixel in each region.
"""
import os

import numpy as np
import tsutils
from timeseries import TimeSeries

import cPickle as pickle
from scipy.interpolate import interp1d

import astropy.units as u

from tstools import is_evenly_sampled
from timeseries import TimeSeries

import details_study as ds


# Apply the window
def apply_window(d, win):
    return d * win


# Apodization windowing function
def DefineWindow(window, nt):
    if window == 'no window':
        win = np.ones(nt)
    if window == 'hanning':
        win = np.hanning(nt)
    if window == 'hamming':
        win = np.hamming(nt)
    winname = ', ' + window
    return win, winname


# Wavelengths we want to analyze
#waves = ['94', '131', '171', '193', '211', '335']
# Regions we are interested in
# regions = ['sunspot', 'loop footpoints', 'quiet Sun', 'moss']
# regions = ['most_of_fov']
# regions = ['four_wavebands']
#regions = ['test_six_euv']


waves = ['171', '193']
regions = ['six_euv']

# Apodization windows
windows = ['hanning']

# Absolute tolerance in seconds when deciding if data is evenly sampled
absolute_tolerance = ds.absolute_tolerance

#
# Main FFT power and time-series characteristic preparation loop
#
for iwave, wave in enumerate(waves):

    for iregion, region in enumerate(regions):

        # branch location
        b = [ds.corename, ds.sunlocation, ds.fits_level, wave, region]

        # Region identifier name
        region_id = ds.datalocationtools.ident_creator(b)

        # Output location
        output = ds.datalocationtools.save_location_calculator(ds.roots, b)["pickle"]

        # Output filename
        ofilename = os.path.join(output, region_id + '.datacube')

        # Go through all the windows
        for iwindow, window in enumerate(windows):
            # General notification that we have a new data-set
            print('\nLoading New Data')
            # Which wavelength?
            print('Wave: ' + wave + ' (%i out of %i)' % (iwave + 1, len(waves)))
            # Which region
            print('Region: ' + region + ' (%i out of %i)' % (iregion + 1, len(regions)))
            # Which window
            print('Window: ' + window + ' (%i out of %i)' % (iwindow + 1, len(windows)))

            # Load the data
            pkl_file_location = os.path.join(output, ofilename + '.pkl')
            print('Loading ' + pkl_file_location)
            pkl_file = open(pkl_file_location, 'rb')
            dc = pickle.load(pkl_file)
            time_information = pickle.load(pkl_file)
            pkl_file.close()

            # Get some properties of the datacube
            ny = dc.shape[0]
            nx = dc.shape[1]
            nt = dc.shape[2]

            # Should be evenly sampled data.  It not, then resample to get
            # evenly sampled data
            t = time_information["time_in_seconds"]
            dt = ds.target_cadence
            ts_evenly_sampled = is_evenly_sampled(t,
                                                  absolute_tolerance.to('s').value)
            if not is_evenly_sampled:
                print('Resampling to an even time cadence.')
                dt = (t[-1] - t[0]) / (1.0 * (nt - 1))
                evenly_sampled_t = np.arange(0, nt) * dt
                for iii in range(0, nx):
                    for jjj in range(0, ny):
                        f = interp1d(t, dc[iii, jjj, :])
                        dc[iii, jjj, :] = f(evenly_sampled_t)
                t = evenly_sampled_t
            else:
                print('Evenly sampled to within tolerance.')

            # Define an array to store the analyzed data
            dc_analysed = np.zeros_like(dc)

            # calculate a window function
            win, dummy_winname = DefineWindow(window, nt)

            # Create a dummy time series object to get some frequency
            # information
            t = dt * np.arange(0, nt)
            tsdummy = TimeSeries(t * u.s, t)

            # Positive frequencies
            pfrequencies = tsdummy.FFTPowerSpectrum.frequencies.pfrequencies

            # The index of the positive frequencies
            pindex = tsdummy.FFTPowerSpectrum.frequencies.pindex

            # Number of positive frequencies
            nposfreq = len(pfrequencies)

            # Storage - Fourier power
            pwr = np.zeros((ny, nx, nposfreq))

            # Storage - Fast Fourier transfrom
            n_fft_freq = len(tsdummy.FFTPowerSpectrum.frequencies.frequencies)
            all_fft = np.zeros((ny, nx, n_fft_freq), dtype=np.complex64)

            # Storage - summary stats
            dtotal = np.zeros((ny, nx))
            dmax = np.zeros_like(dtotal)
            dmin = np.zeros_like(dtotal)
            dsd = np.zeros_like(dtotal)
            dlnsd = np.zeros_like(dtotal)

            for i in range(0, nx):
                for j in range(0, ny):

                    # Get the next time-series
                    d = dc[j, i, :].flatten()

                    # Fix the data for any non-finite entries
                    d = tsutils.fix_nonfinite(d)

                    # ---
                    # Basic statistics of the time series
                    # Get the total emission
                    dtotal[j, i] = np.sum(d)

                    # Get the maximum emission
                    dmax[j, i] = np.max(d)

                    # Get the minimum emission
                    dmin[j, i] = np.min(d)

                    # Get the standard deviation of the emission
                    dsd[j, i] = np.std(d)

                    # Get the standard deviation of the log of the emission
                    dlnsd[j, i] = np.std(np.log(d))

                    # ---
                    # Fourier transform of the absolute intensities
                    # Multiply the data by the apodization window
                    d_with_window = apply_window(d, win)

                    # Get the Fourier transform
                    this_fft = np.fft.fft(d_with_window)

                    # Fourier power of the absolute intensities
                    this_power = ((np.abs(this_fft) ** 2) / (1.0 * nt))[pindex]

                    # Store the individual Fourier power
                    pwr[j, i, :] = this_power

                    # Store the full FFT
                    all_fft[j, i, :] = this_fft

                    # ---
                    # Relative change in intensity
                    dmean = np.mean(d)
                    d_relative_change = (d - dmean) / dmean
                    d_relative_change_with_window = apply_window(d_relative_change, win)
                    this_fft_relative_change_with_window = np.fft.fft(d_relative_change_with_window)
                    this_power_relative_change_with_window = ((np.abs(this_fft_relative_change_with_window) ** 2) / (1.0 * nt))[pindex]

                    # ---
                    # Ireland et al (2015) summation
                    # Sum over the log(Fourier power of the relative intensities)

                    # ---
                    # Sum over the log(Fourier power of the absolute intensities)

                    # ---
                    # Sum over the Fourier power of the relative intensities

                    # ---
                    # Sum over the Fourier power of the absolute intensities

            # Save the Fourier power of the absolute intensities
            ofilename = ofilename + '.' + window
            filepath = os.path.join(output, ofilename + '.fourier_power.pkl')
            print('Saving power spectra to ' + filepath)
            f = open(filepath, 'wb')
            pickle.dump(pfrequencies, f)
            pickle.dump(pwr, f)
            f.close()

            # Save the FFT of the analyzed time-series
            filepath = os.path.join(output, ofilename + '.fourier_transform.pkl')
            print('Saving Fourier transform to ' + filepath)
            f = open(filepath, 'wb')
            pickle.dump(pfrequencies, f)
            pickle.dump(all_fft, f)
            f.close()

            # Save the summary statistics
            filepath = os.path.join(output, ofilename + '.summary_stats.npz')
            print('Saving summary statistics to ' + filepath)
            np.savez(filepath, dtotal=dtotal, dmax=dmax, dmin=dmin, dsd=dsd, dlnsd=dlnsd)
