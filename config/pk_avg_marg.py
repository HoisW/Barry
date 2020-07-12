import sys
import os
import pandas as pd
from scipy.interpolate import interp1d
from scipy.stats import norm
import numpy as np


sys.path.append("..")
from barry.datasets.dataset_power_spectrum import PowerSpectrum_Beutler2019_Z061_NGC
from barry.cosmology.camb_generator import getCambGenerator
from barry.postprocessing import BAOExtractor
from barry.config import setup
from barry.models import PowerSeo2016, PowerBeutler2017, PowerDing2018
from barry.samplers import DynestySampler, EnsembleSampler
from barry.fitter import Fitter
from barry.models.model import Correction

if __name__ == "__main__":
    pfn, dir_name, file = setup(__file__)

    c = getCambGenerator()
    r_s = c.get_data()["r_s"]
    p = BAOExtractor(r_s)

    sampler = DynestySampler(temp_dir=dir_name, nlive=1000)
    # sampler = EnsembleSampler(temp_dir=dir_name, num_steps=5000)
    fitter = Fitter(dir_name)

    cs = ["#262232", "#116A71", "#48AB75"]

    for r in [False]:
        t = "Recon" if r else "Prerecon"
        ls = "-"  # if r else "--"
        d = PowerSpectrum_Beutler2019_Z061_NGC(recon=r, isotropic=True, reduce_cov_factor=np.sqrt(2000.0))

        # Fix sigma_nl for one of the Beutler models
        model = PowerBeutler2017(recon=r, isotropic=d.isotropic, fix_params=["om"], correction=Correction.HARTLAP)
        model_marg = PowerBeutler2017(recon=r, isotropic=d.isotropic, fix_params=["om"], correction=Correction.HARTLAP, marg=True)
        model_fixed = PowerBeutler2017(
            recon=r,
            isotropic=d.isotropic,
            fix_params=["om", "b", f"a{{0}}_1", f"a{{0}}_2", f"a{{0}}_3", f"a{{0}}_4", f"a{{0}}_5"],
            correction=Correction.HARTLAP,
        )
        model_fixed.set_default("b", 1.591)
        model_fixed.set_default(f"a{{0}}_1", 4651.0)
        model_fixed.set_default(f"a{{0}}_2", -4882.0)
        model_fixed.set_default(f"a{{0}}_3", 2137.0)
        model_fixed.set_default(f"a{{0}}_4", -25.43)
        model_fixed.set_default(f"a{{0}}_5", 0.01628)

        fitter.add_model_and_dataset(model, d, name=f"Full Fit", linestyle=ls, color=cs[0])
        fitter.add_model_and_dataset(model_marg, d, name=f"Analytic", linestyle=ls, color=cs[1])
        fitter.add_model_and_dataset(model_fixed, d, name=f"Fixed Bias+Poly", linestyle=ls, color=cs[2])
    fitter.set_sampler(sampler)
    fitter.set_num_walkers(10)
    fitter.fit(file)

    if fitter.should_plot():
        import logging

        logging.info("Creating plots")

        from chainconsumer import ChainConsumer

        c = ChainConsumer()
        for posterior, weight, chain, evidence, model, data, extra in fitter.load():
            print(chain[np.argmax(posterior)])
            params = model.get_labels()
            if len(params) == 9:
                params[1] = "$b^{2}$"
                params[4:] = ["$a^{1}_{0}$", "$a^{2}_{0}$", "$a^{3}_{0}$", "$a^{4}_{0}$", "$a^{5}_{0}$"]
            c.add_chain(chain, weights=weight, parameters=params, **extra)
        c.configure(shade=True, legend_artists=True, max_ticks=4, sigmas=[0, 1, 2, 3], label_font_size=16, tick_font_size=12, kde=True)
        truth = {"$\\alpha$": 1.0}
        c.plotter.plot_summary(filename=[pfn + "_summary.png", pfn + "_summary.pdf"], errorbar=True)
        c.plotter.plot(
            figsize="COLUMN",
            filename=[pfn + "_contour.png", pfn + "_contour.pdf"],
            parameters=["$\\alpha$", "$\\Sigma_s$", "$\\Sigma_{nl}$"],
            extents={"$\\alpha$": (0.985, 1.020), "$\\Sigma_s$": (4.0, 16.0), "$\\Sigma_{nl}$": (8.0, 11.0)},
        )
        c.plotter.plot(
            figsize="PAGE",
            filename=[pfn + "_contour2.png", pfn + "_contour2.pdf"],
            parameters=[
                "$\\alpha$",
                "$\\Sigma_s$",
                "$\\Sigma_{nl}$",
                "$b^{2}$",
                "$a^{1}_{0}$",
                "$a^{2}_{0}$",
                "$a^{3}_{0}$",
                "$a^{4}_{0}$",
                "$a^{5}_{0}$",
            ],
            extents={
                "$\\alpha$": (0.985, 1.020),
                "$\\Sigma_s$": (4.0, 16.0),
                "$\\Sigma_{nl}$": (8.0, 11.0),
                "$b^{2}$": (0.8, 2.4),
                "$a^{1}_{0}$": (-4000.0, 10000.0),
                "$a^{2}_{0}$": (-8000.0, 1000.0),
                "$a^{3}_{0}$": (1000.0, 2800.0),
                "$a^{4}_{0}$": (-60.0, 20.0),
                "$a^{5}_{0}$": (-0.03, 0.05),
            },
        )
        c.plotter.plot_walks(filename=pfn + "_walks.png")
        c.analysis.get_latex_table(filename=pfn + "_params.txt")
