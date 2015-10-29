#
# Analysis - examine the lognormal fit.
#
# This program creates the following plots
#
# (1)
# Distributions of the position of the lognormal
# (2)
# Distribution of the location of the maximum of the ratio of the lognormal
# contribution to the background power law
# (3)
# Distribution of the maximum of the ratio of the lognormal contribution to the
# background power law
# (4)
# Distributions of the energy flux from each contribution
#
import os
import copy
import numpy as np
import matplotlib.pyplot as plt
from astroML.plotting import hist
import astropy.units as u
import analysis_get_data
import analysis_explore
import study_details as sd
import summary_statistics, get_mode, get_image_model_location
import details_analysis as da
import details_plots as dp

# Wavelengths we want to analyze
waves = ['211']

# Regions we are interested in
regions = ['sunspot', 'quiet Sun']
#regions = ['most_of_fov']
# Apodization windows
windows = ['hanning']

# Model results to examine
model_names = ('Power Law + Constant + Lognormal',)

# Model results to examine
model_comparison_names = ('Power Law + Constant + Lognormal', 'Power Law + Constant')

# Load in all the data
storage = analysis_get_data.get_all_data(waves=waves,
                                         regions=regions,
                                         model_names=model_comparison_names)

masks = analysis_explore.MaskDefine(storage)

#
# Details of the analysis
#
limits = da.limits
ic_types = da.ic_details.keys()

#
# Details of the plotting
#
fz = dp.fz
three_minutes = (1.0 / dp.three_minutes).to(fz).value
five_minutes = (1.0 / dp.five_minutes).to(fz).value
hloc = dp.hloc


# Period limit
ratio_limit = limits["ratio"]


linewidth = 3

#
plot_type = 'cc.within'
for wave in waves:
    for region in regions:

        # branch location
        b = [sd.corename, sd.sunlocation, sd.fits_level, wave, region]

        # Region identifier name
        region_id = sd.datalocationtools.ident_creator(b)

        # Output location
        output = sd.datalocationtools.save_location_calculator(sd.roots, b)["pickle"]

        for this_model in model_names:
            for ic_type in ic_types:

                # Get the IC limit
                ic_limit = da.ic_details[ic_type]

                # Next data set
                this = storage[wave][region][this_model]

                # List of parameters
                parameters = [v.fit_parameter for v in this.model.variables]

                # Frequencies
                f = this.f
                if not isinstance(f, u.Quantity):
                    f = f * u.Hz
                fn = this.fn  # normalized frequencies (no units)

                # Mask
                mask1 = masks.combined_good_fit_parameter_limit[wave][region][this_model]
                mask2 = masks.is_this_model_preferred(ic_type, ic_limit, this_model)[wave][region]
                mask = np.logical_or(mask1, mask2)

                ##############################################################
                #
                # Plot a histogram of the position of the lognormal
                #
                p1_name = 'lognormal position'
                p1 = this.as_array(p1_name).to(fz)

                # Create the masked data
                p1 = np.ma.array(p1, mask=mask).compressed()

                # Summary stats
                ss = summary_statistics(p1)

                # Identifier of the plot
                plot_identity = wave + '.' + region + '.%s.' + ic_type + '>%f' % (p1_name, ic_limit)

                # Title of the plot
                title = plot_identity + dp.get_mask_info_string(mask)

                # location of the image
                image = get_image_model_location(sd.roots, b, [this_model, ic_type])

                # Plot the same data using all the bin choices.
                plt.close('all')
                plt.figure(1, figsize=(10, 10))
                for ibinning, binning in enumerate(hloc):
                    plt.subplot(len(hloc), 1, ibinning+1)
                    plt.hist(p1, bins=binning)
                    plt.axvline(ss['mean'].value, color='r', label='mean=%f %s' % (ss['mean'].value, fz), linewidth=linewidth)
                    plt.axvline(ss['mode'].value, color='g', label='mode=%f %s' % (ss['mode'].value, fz), linewidth=linewidth)
                    plt.axvline(five_minutes, color='k', label='5 minutes', linestyle="-", linewidth=linewidth)
                    plt.axvline(three_minutes, color='k', label='3 minutes', linestyle=":", linewidth=linewidth)
                    plt.xlabel(p1_name + ' (%s)' % fz)
                    plt.title(str(binning) + ' : %s\n%s' % (title, this_model))
                    plt.legend(framealpha=0.5, fontsize=8)

                plt.tight_layout()
                ofilename = this_model + '.' + plot_identity + '.hist.png'
                plt.savefig(os.path.join(image, ofilename))

                ##############################################################
                #
                # Maximum value of the ratio of the lognormal component to the
                # power law at the
                #
                # Ratio maximum
                ratio_max = np.zeros((this.ny, this.nx))

                # Normalized frequency at which the ratio maximum occurs
                ratio_max_fn = np.zeros_like(ratio_max)

                # Calculate the ratio maximum and the frequency it occurs at
                for i in range(0, this.nx):
                    for j in range(0, this.ny):
                        estimate = this.result[j][i][1]['x']
                        power_law = this.model.power_per_component(estimate, fn)[0]
                        lognormal = this.model.power_per_component(estimate, fn)[2]
                        ratio = lognormal/power_law
                        ratio_max[j, i] = np.log10(np.max(ratio))
                        ratio_max_fn[j, i] = fn[np.argmax(ratio)]

                # Make a mask for these data
                ratio_max_mask = copy.deepcopy(mask)
                too_small = np.where(ratio_max < limits['ratio'][0])
                too_big = np.where(ratio_max > limits['ratio'][1])
                ratio_max_mask[too_small] = True
                ratio_max_mask[too_big] = True
                ratio_max = np.ma.array(ratio_max, mask=ratio_max_mask).compressed()
                ratio_max_fn = np.ma.array(ratio_max_fn, mask=ratio_max_mask).compressed()

                # Summary stats
                ss = summary_statistics(ratio_max)

                # Identifier of the plot
                plot_identity = wave + '.' + region + '.max(lognormal/power law).' + ic_type + '>%f' % ic_limit

                # Title of the plot
                title = plot_identity + dp.get_mask_info_string(ratio_max_mask)

                # Plot
                plt.close('all')
                plt.figure(1, figsize=(10, 10))
                for ibinning, binning in enumerate(hloc):
                    plt.subplot(len(hloc), 1, ibinning+1)
                    h_info = hist(ratio_max, bins=binning)
                    plt.axvline(ss['mean'], color='r', label='mean=%f' % ss['mean'], linewidth=linewidth)
                    plt.axvline(ss['mode'], color='g', label='mode=%f' % ss['mode'], linewidth=linewidth)
                    plt.xlabel('$log_{10}\max$(lognormal/power law)')
                    plt.title(str(binning) + ' : %s\n%s' % (title, this_model))
                    plt.legend(framealpha=0.5, fontsize=8)
                    plt.xlim(ratio_limit)

                plt.tight_layout()
                ofilename = this_model + '.' + plot_identity + '.hist.png'
                plt.savefig(os.path.join(image, ofilename))

                ##############################################################
                #
                # Location of the ratio maximum.  This is meant to signify the
                # frequency where the lognormal is most likely to be detected.
                #
                rmf_data = (f[0] * np.ma.getdata(ratio_max_fn)).to(fz).value
                rmf_mask = np.ma.getmask(ratio_max_fn)
                too_small = np.where(rmf_data < limits['frequency']).to(fz).value
                too_big = np.where(rmf_data > limits['frequency']).to(fz).value
                rmf_mask[too_small] = True
                rmf_mask[too_big] = True

                ratio_max_f = np.ma.array(rmf_data * u.Unit(fz), mask=rmf_mask).compressed()

                # Summary stats
                ss = summary_statistics(ratio_max_f)

                # Identifier of the plot
                plot_identity = wave + '.' + region + '.argmax(lognormal/power law).' + ic_type + '>%f' % ic_limit

                # Title of the plot
                title = plot_identity + dp.get_mask_info_string(ratio_max_mask)

                # Plot
                plt.close('all')
                plt.figure(1, figsize=(10, 10))
                for ibinning, binning in enumerate(hloc):
                    plt.subplot(len(hloc), 1, ibinning+1)
                    h_info = hist(ratio_max_f, bins=binning)
                    plt.axvline(ss['mean'].value, color='r', label='mean=%f %s' % (ss['mean'].value, fz), linewidth=linewidth)
                    plt.axvline(ss['mode'].value, color='g', label='mode=%f %s' % (ss['mode'].value, fz), linewidth=linewidth)
                    plt.axvline(five_minutes, color='k', label='5 minutes', linestyle="-", linewidth=linewidth)
                    plt.axvline(three_minutes, color='k', label='3 minutes', linestyle=":", linewidth=linewidth)
                    plt.xlabel('argmax(lognormal / power law) (%s)' % fz)
                    plt.title(str(binning) + ' : %s\n%s' % (title, this_model))
                    plt.legend(framealpha=0.5, fontsize=8)

                plt.tight_layout()
                ofilename = this_model + '.' + plot_identity + '.hist.png'
                plt.savefig(os.path.join(image, ofilename))

                ###############################################################
                #
                # Find the frequency at which the estimated power law component
                # is equal to the estimated constant background.  The constant
                # component of the power spectrum model dominates at frequencies
                # above this frequency.
                #
                # Background value
                p_background = this.as_array('constant')

                # Amplitude of the power law
                p_power_law_amplitude = this.as_array('power law amplitude')

                # Power law index
                p_power_law_index = this.as_array('power law index')

                # Normalized frequency where equivalency is reached
                normalized_equivalency_frequency = (p_background / p_power_law_amplitude) ** (-1.0/p_power_law_index)

                # Find the value of the equivalency frequency
                equivalency_frequency = (f[0] * normalized_equivalency_frequency).to(fz).value

                # Make a mask for these data
                ef_mask = copy.deepcopy(mask)
                too_small = np.where(equivalency_frequency < limits['frequency']).to(fz).value
                too_big = np.where(equivalency_frequency > limits['frequency']).to(fz).value
                ef_mask[too_small] = True
                ef_mask[too_big] = True

                equivalency_frequency = np.ma.array(equivalency_frequency * u.Unit(fz),
                                                    mask=ef_mask).compressed()

                # Summary stats
                ss = summary_statistics(equivalency_frequency)

                # Identifier of the plot
                plot_identity = wave + '.' + region + '.equivalency_frequency.' + ic_type + '>%f' % ic_limit

                # Title of the plot
                title = plot_identity + dp.get_mask_info_string(ratio_max_mask)

                # Plot
                plt.close('all')
                plt.figure(1, figsize=(10, 10))
                for ibinning, binning in enumerate(hloc):
                    plt.subplot(len(hloc), 1, ibinning+1)
                    h_info = hist(ratio_max, bins=binning)
                    plt.axvline(ss['mean'], color='r', label='mean=%f' % ss['mean'], linewidth=linewidth)
                    plt.axvline(ss['mode'], color='g', label='mode=%f' % ss['mode'], linewidth=linewidth)
                    plt.axvline(five_minutes, color='k', label='5 minutes', linestyle="-", linewidth=linewidth)
                    plt.axvline(three_minutes, color='k', label='3 minutes', linestyle=":", linewidth=linewidth)
                    plt.xlabel('equivalency frequency')
                    plt.title(str(binning) + ' : %s\n%s' % (title, this_model))
                    plt.legend(framealpha=0.5, fontsize=8)
                    plt.xlim(ratio_limit)

                plt.tight_layout()
                ofilename = this_model + '.' + plot_identity + '.hist.png'
                plt.savefig(os.path.join(image, ofilename))
