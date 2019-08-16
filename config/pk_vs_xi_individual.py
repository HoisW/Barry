import sys

sys.path.append("..")
from barry.framework.cosmology.camb_generator import getCambGenerator
from barry.setup import setup
from barry.framework.models import PowerSeo2016, PowerBeutler2017, PowerDing2018, CorrBeutler2017, CorrSeo2016, CorrDing2018
from barry.framework.datasets import PowerSpectrum_SDSS_DR7_Z015, CorrelationFunction_SDSS_DR12_Z061_NGC
from barry.framework.samplers.ensemble import EnsembleSampler
from barry.framework.fitter import Fitter
import numpy as np

if __name__ == "__main__":
    pfn, dir_name, file = setup(__file__)
    fitter = Fitter(dir_name, save_dims=2, remove_output=False)

    c = getCambGenerator()
    r_s, _ = c.get_data()

    sampler = EnsembleSampler(temp_dir=dir_name, num_walkers=100, num_steps=500, num_burn=300)

    for r in [True]:
        t = "Recon" if r else "Prerecon"

        d_pk = PowerSpectrum_SDSS_DR7_Z015(recon=r, realisation=0)
        d_xi = CorrelationFunction_SDSS_DR12_Z061_NGC(recon=r, realisation=0)

        beutler_pk = PowerBeutler2017(recon=r)
        seo_pk = PowerSeo2016(recon=r)
        ding_pk = PowerDing2018(recon=r)

        beutler_xi = CorrBeutler2017()
        seo_xi = CorrSeo2016(recon=r)
        ding_xi = CorrDing2018(recon=r)

        for i in range(999):
            d_pk.set_realisation(i)
            d_xi.set_realisation(i)

            fitter.add_model_and_dataset(beutler_pk, d_pk, name=f"Beutler 2017 P(k), mock number {i}", linestyle="-", color="p")
            fitter.add_model_and_dataset(seo_pk, d_pk, name=f"Seo 2016 P(k), mock number {i}", linestyle="-", color="r")
            fitter.add_model_and_dataset(ding_pk, d_pk, name=f"Ding 2018 P(k), mock number {i}", linestyle="-", color="lb")

            fitter.add_model_and_dataset(beutler_xi, d_xi, name=f"Beutler 2017 corr, mock number {i}", linestyle=":", color="p")
            fitter.add_model_and_dataset(seo_xi, d_xi, name=f"Seo 2016 corr, mock number {i}", linestyle=":", color="r")
            fitter.add_model_and_dataset(ding_xi, d_xi, name=f"Ding 2018 corr, mock number {i}", linestyle=":", color="lb")

    fitter.set_sampler(sampler)
    fitter.set_num_walkers(1)
    fitter.set_num_cpu(400)
    if not fitter.should_plot():
        fitter.fit(file)

    if fitter.should_plot():
        import matplotlib.pyplot as plt

        import logging
        logging.info("Creating plots")

        res = {}
        for posterior, weight, chain, model, data, extra in fitter.load():
            n = extra["name"].split(",")[0]
            if res.get(n) is None:
                res[n] = []
            i = posterior.argmax()
            chi2 = - 2 * posterior[i]
            res[n].append([chain[:, 0].mean(), np.std(chain[:, 0]), chain[i, 0], posterior[i], chi2, -chi2])
        for label in res.keys():
            res[label] = np.array(res[label])
        smooth_prerecon = res["Smooth Prerecon"]
        smooth_recon = res["Smooth Recon"]
        for label, values in res.items():
            smooth = smooth_prerecon if "Prerecon" in label else smooth_recon
            values[:, -1] += smooth[:, -2]    
        ks = [l for l in res.keys() if "Smooth" not in l]

        # Define colour scheme
        c2 = ["#225465", "#5FA45E"] # ["#581d7f", "#e05286"]
        c3 = ["#2C455A", "#258E71", "#C1C64D"] # ["#501b73", "#a73b8f", "#ee8695"]
        c4 = ["#262232","#116A71","#48AB75","#D1E05B"] #["#461765", "#7b2a95", "#d54d88", "#f19a9b"]
        c5 = ["#262232", "#1F4D5C", "#0E7A6E", "#5BA561", "#C1C64D"] # ["#3c1357", "#61208d", "#a73b8f", "#e8638b", "#f4aea3"]
        cols = {"Beutler": c4[0], "Seo": c4[1], "Ding": c4[2], "Noda": c4[3]}

        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
        # chi2 comparison
        if False:
            
            for k in ks:
                plt.hist(res[k][:, -1], label=k, lw=2, histtype='step', bins=20)
            plt.legend(loc=2)
            plt.axvline(4)
            plt.xlabel(r"$\Delta \chi^2$")
              
        if False:
            import pandas as pd
            import seaborn as sb
            alphas = np.vstack((res[k][:, 0] for k in ks))
            df = pd.DataFrame(alphas.T, columns=ks)
            fig, ax = plt.subplots(figsize=(6, 6))
            sb.heatmap(df.corr(), annot=True, cmap="viridis", fmt="0.2f", square=True, ax=ax, cbar=False)
            fig.savefig(pfn + "_corr.png", bbox_inches="tight", dpi=300, transparent=True)
            fig.savefig(pfn + "_corr.pdf", bbox_inches="tight", dpi=300, transparent=True)
            
        # Make histogram comparison
        if True:
            fig, axes = plt.subplots(nrows=2, figsize=(5, 4), sharex=True)
            bins = np.linspace(0.8, 1.15, 31)
            for label, means in res.items():
                if "Smooth" in label:
                    continue
                if "Prerecon" in label:
                    ax = axes[0]
                else:
                    ax = axes[1]
                c = cols[label.split()[0]]
                ax.hist(means[:, 0], bins=bins, label=" ".join(label.split()[:-1]), histtype="stepfilled", linewidth=2, alpha=0.3, color=c)
                ax.hist(means[:, 0], bins=bins, histtype="step", linewidth=1.5, color=cols[label.split()[0]])
            axes[1].set_xlabel(r"$\langle \alpha \rangle$", fontsize=14)
            axes[0].set_yticklabels([])
            axes[1].set_yticklabels([])
            axes[0].axvline(1.0, color="k", lw=1, ls="--", alpha=0.6)
            axes[1].axvline(1.0, color="k", lw=1, ls="--", alpha=0.6)
            axes[0].annotate("Prerecon", (0.98, 0.96), xycoords="axes fraction", horizontalalignment="right", verticalalignment="top")
            axes[1].annotate("Recon", (0.98, 0.96), xycoords="axes fraction", horizontalalignment="right", verticalalignment="top")
            #leg1 = axes[0].legend(loc=2, frameon=False)
            leg2 = axes[1].legend(loc=2, frameon=False)
            for lh in leg2.legendHandles:
                lh.set_alpha(1)
            axes[0].tick_params(axis='y', left=False)
            axes[1].tick_params(axis='y', left=False)
            plt.subplots_adjust(hspace=0.0)
            fig.savefig(pfn + "_alphahist.png", bbox_inches="tight", dpi=300, transparent=True)
            fig.savefig(pfn + "_alphahist.pdf", bbox_inches="tight", dpi=300, transparent=True)

        # Make histogram comparison
        if True:
            fig, axes = plt.subplots(nrows=2, figsize=(5, 4), sharex=True)
            bins = np.linspace(0.01, 0.2, 31)
            for label, means in res.items():
                if "Smooth" in label:
                    continue
                if "Prerecon" in label:
                    ax = axes[0]
                else:
                    ax = axes[1]
                c = cols[label.split()[0]]
                ax.hist(means[:, 1], bins=bins, label=label, histtype="stepfilled", linewidth=2, alpha=0.3, color=c)
                ax.hist(means[:, 1], bins=bins, histtype="step", linewidth=1.5, color=cols[label.split()[0]])
            axes[1].set_xlabel(r"$\langle \alpha \rangle$", fontsize=14)
            axes[0].set_yticklabels([])
            axes[1].set_yticklabels([])
            #axes[0].axvline(1.0, color="k", lw=1, ls="--", alpha=0.6)
            #axes[1].axvline(1.0, color="k", lw=1, ls="--", alpha=0.6)
            leg1 = axes[0].legend(loc=1, frameon=False)
            leg2 = axes[1].legend(loc=1, frameon=False)
            for lh in leg1.legendHandles + leg2.legendHandles: 
                lh.set_alpha(1)
            #axes[0].tick_params(axis='y', left=False)
            #axes[1].tick_params(axis='y', left=False)
            plt.subplots_adjust(hspace=0.0)
            fig.savefig(pfn + "_alphaerrhist.png", bbox_inches="tight", dpi=300, transparent=True)
            fig.savefig(pfn + "_alphaerrhist.pdf", bbox_inches="tight", dpi=300, transparent=True)

        from matplotlib.colors import to_rgb, to_hex
        def blend_hex(hex1, hex2):
            a = np.array(to_rgb(hex1))
            b = np.array(to_rgb(hex2))
            return to_hex(0.5 * (a + b))
                
        # Alpha-alpha comparison
        if True:
            from scipy.interpolate import interp1d
            bins = np.linspace(0.73, 1.15, 31)
            cols = {"Beutler": c4[0], "Seo": c4[1], "Ding": c4[2], "Noda": c4[3]}
            fig, axes = plt.subplots(4, 4, figsize=(10, 10), sharex=True)
            labels = ["Beutler 2017 Recon", "Seo 2016 Recon", "Ding 2018 Recon", "Noda 2019 Recon"]
            #labels = ["Beutler Prerecon", "Seo Prerecon", "Ding Prerecon", "Noda Prerecon"]
            for i, label1 in enumerate(labels):
                for j, label2 in enumerate(labels):
                    ax = axes[i, j]
                    if i < j:
                        ax.axis('off')
                        continue
                    elif i == j:
                        h, _, _ = ax.hist(res[label1][:, 0], bins=bins, histtype="stepfilled", linewidth=2, alpha=0.3, color=cols[label1.split()[0]])
                        ax.hist(res[label1][:, 0], bins=bins, histtype="step", linewidth=1.5, color=cols[label1.split()[0]])
                        ax.set_yticklabels([])
                        ax.tick_params(axis='y', left=False)
                        ax.set_xlim(0.85, 1.16)
                        yval = interp1d(0.5 * (bins[:-1] + bins[1:]), h, kind="nearest")([1.0])[0]
                        ax.plot([1.0, 1.0], [0, yval], color="k", lw=1, ls="--", alpha=0.4)
                        ax.spines['right'].set_visible(False)
                        ax.spines['top'].set_visible(False)
                        if j == 0:
                            ax.spines['left'].set_visible(False)
                        if j == 3:
                            ax.set_xlabel(label2, fontsize=12)
                            ax.set_xticks([0.9, 1.0, 1.1])
                    else:
                        print(label1, label2)
                        a1 = np.array(res[label2][:, 0])
                        a2 = np.array(res[label1][:, 0])
                        c = blend_hex(cols[label1.split()[0]], cols[label2.split()[0]])
                        c = np.abs(a1 - a2)
                        ax.scatter(a1, a2, s=2, c=c, cmap="viridis_r", vmin=-0.01, vmax=0.15)
                        ax.set_xlim(0.85, 1.16)
                        ax.set_ylim(0.85, 1.16)
                        ax.plot([0.8, 1.2], [0.8, 1.2], c="k", lw=1, alpha=0.8, ls=":")
                        ax.axvline(1.0, color="k", lw=1, ls="--", alpha=0.4)
                        ax.axhline(1.0, color="k", lw=1, ls="--", alpha=0.4)
                        
                        if j != 0:
                            ax.set_yticklabels([])
                            ax.tick_params(axis='y', left=False)
                        else:
                            ax.set_ylabel(label1, fontsize=12)
                            ax.set_yticks([0.9, 1.0, 1.1])
                        if i == 3:
                            ax.set_xlabel(label2, fontsize=12)
                            ax.set_xticks([0.9, 1.0, 1.1])
            plt.subplots_adjust(hspace=0.0, wspace=0)
            fig.savefig(pfn + "_alphacomp.png", bbox_inches="tight", dpi=300, transparent=True)
            fig.savefig(pfn + "_alphacomp.pdf", bbox_inches="tight", dpi=300, transparent=True)

        if False:
            from scipy.interpolate import interp1d
            bins = np.linspace(0.02, 0.17, 31)
            cols = {"Beutler": c4[0], "Seo": c4[1], "Ding": c4[2], "Noda": c4[3]}
            fig, axes = plt.subplots(4, 4, figsize=(10, 10), sharex=True)
            labels = ["Beutler 2017 Recon", "Seo 2016 Recon", "Ding 2018 Recon", "Noda 2019 Recon"]
            #labels = ["Beutler Prerecon", "Seo Prerecon", "Ding Prerecon", "Noda Prerecon"]
            v1, v2 = 0.01, 0.17
            for i, label1 in enumerate(labels):
                for j, label2 in enumerate(labels):
                    ax = axes[i, j]
                    if i < j:
                        ax.axis('off')
                        continue
                    elif i == j:
                        h, _, _ = ax.hist(res[label1][:, 1], bins=bins, histtype="stepfilled", linewidth=2, alpha=0.3, color=cols[label1.split()[0]])
                        ax.hist(res[label1][:, 1], bins=bins, histtype="step", linewidth=1.5, color=cols[label1.split()[0]])
                        ax.set_yticklabels([])
                        ax.tick_params(axis='y', left=False)
                        ax.set_xlim(v1, v2)
                        ax.spines['right'].set_visible(False)
                        ax.spines['top'].set_visible(False)
                        if j == 0:
                            ax.spines['left'].set_visible(False)
                        if j == 3:
                            ax.set_xlabel(label2, fontsize=12)
                            #ax.set_xticks([0.9, 1.0, 1.1])
                    else:
                        print(label1, label2)
                        a1 = np.array(res[label2][:, 1])
                        a2 = np.array(res[label1][:, 1])
                        c = blend_hex(cols[label1.split()[0]], cols[label2.split()[0]])
                        c = np.abs(a1 - a2)
                        ax.scatter(a1, a2, s=2, c=c, cmap="viridis_r", vmin=-0.01, vmax=0.15)
                        ax.set_xlim(v1, v2)
                        ax.set_ylim(v1, v2)
                        ax.plot([v1, v2], [v1, v2], c="k", lw=1, alpha=0.8, ls=":")
                        #ax.axvline(1.0, color="k", lw=1, ls="--", alpha=0.4)
                        #ax.axhline(1.0, color="k", lw=1, ls="--", alpha=0.4)
                        
                        if j != 0:
                            ax.set_yticklabels([])
                            ax.tick_params(axis='y', left=False)
                        else:
                            ax.set_ylabel(label1, fontsize=12)
                            #ax.set_yticks([0.9, 1.0, 1.1])
                        if i == 3:
                            ax.set_xlabel(label2, fontsize=12)
                            #ax.set_xticks([0.9, 1.0, 1.1])
            plt.subplots_adjust(hspace=0.0, wspace=0)
            fig.savefig(pfn + "_alphaerrcomp.png", bbox_inches="tight", dpi=300, transparent=True)
            fig.savefig(pfn + "_alphaerrcomp.pdf", bbox_inches="tight", dpi=300, transparent=True)