#!/usr/bin/env python3
"""Plot published stage readbacks and measured hook cycles; no hardware access."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    receipt=json.loads(args.receipt.read_text())
    if receipt.get('kind')!='esp32-register-observation-v1' or not receipt.get('records'):
        parser.error('Requires an independently wire-bound register receipt with observed stages')
    records=receipt['records']
    colors={'post_settings':'#f7d572','before_acquire':'#5cc8ff',
            'armed_before_trigger':'#baadff','dump_complete':'#73dda6',
            'restored_after_dump':'#ffad85'}
    plt.rcParams.update({'svg.fonttype':'none','font.family':'DejaVu Sans','font.size':10})
    fig,axes=plt.subplots(3,1,figsize=(11,7),sharex=True,gridspec_kw={'height_ratios':[1,1,1.6]})
    fig.patch.set_facecolor('#101827')
    for ax in axes:
        ax.set_facecolor('#172336')
        ax.tick_params(colors='#cbd8e8')
        ax.yaxis.label.set_color('#e7eef7')
        for spine in ax.spines.values():spine.set_color('#405168')
        ax.grid(alpha=.2,color='#9aafc9')
    for stage,color in colors.items():
        selected=[r for r in records if r['stage']==stage]
        for ax,key in zip(axes,('selector','bit23','hook_cycles')):
            ax.scatter([r['sequence'] for r in selected],[r[key] for r in selected],
                       s=19,color=color,label=stage.replace('_',' '),zorder=3)
    axes[0].set_ylabel('Forced-selector field')
    axes[0].set_ylim(-5,132)
    axes[0].set_yticks([0,48,96,127])
    axes[1].set_ylabel('Manual-enable bit23')
    axes[1].set_ylim(-.15,1.15)
    axes[1].set_yticks([0,1])
    axes[2].set_ylabel('Hook-body elapsed cycles\n(raw modular CCOUNT)')
    axes[2].set_ylim(bottom=0)
    axes[2].set_xlabel('Observed stage sequence (initial read, then four stages per capture)',color='#e7eef7')
    axes[2].set_xlim(-1,81)
    axes[2].set_xticks([0,20,40,60,80])
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.925),ncol=3,
               facecolor='#172336',edgecolor='#405168',labelcolor='#e7eef7',fontsize=9)
    fig.suptitle(f"Actual ESP register observations · {len(records)} stages · {receipt['status']}",
                 color='#e7eef7',fontsize=15,y=.985)
    fig.text(.07,.028,'Sampled field readback is not calibrated analog gain or continuous state.\n'
             'Cycles include interrupts/preemption; counter wrap and residual measurement cost remain uncalibrated.',
             color='#cbd8e8',fontsize=9)
    fig.subplots_adjust(left=.13,right=.97,top=.82,bottom=.16,hspace=.28)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,metadata={'Date':None,'Description':'Actual integrity-bound ESP stage readbacks; no RF reception claim.'})
    plt.close(fig)


if __name__=='__main__':main()
