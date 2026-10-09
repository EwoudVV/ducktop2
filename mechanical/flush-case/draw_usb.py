#!/usr/bin/env python3
"""Draw the saved old and revised USB power paths at the same scale."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
import numpy as np

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'case-prototype/installed-power-harness.json'
old=[r for r in json.loads(OLD.read_text())['routes'] if r['group']=='usb5']
new=json.loads((HERE/'usb-harness.json').read_text())['routes']
fig,axs=plt.subplots(2,1,figsize=(14,9),facecolor='#faf9f5')
for ax,title,rows in [(axs[0],'previous route under the trackpad',old),(axs[1],'shorter route behind the keyboard',new)]:
    ax.set_facecolor('#faf9f5')
    ax.add_patch(Rectangle((42.25,20),273.5,80,fc='#d2d7dc',ec='#82919f',alpha=.7))
    ax.text(179,94,'keyboard',ha='center',fontsize=11,color='#4f5a68')
    ax.add_patch(Rectangle((107,141),144,109,fc='#c7dce5',ec='#5e8494',alpha=.65))
    ax.text(179,167,'trackpad support',ha='center',fontsize=11,color='#346378')
    ax.add_patch(Rectangle((145,150.2),80,36.148,fc='none',ec='#609579',lw=1.2,ls='--'))
    ax.add_patch(Circle((309,152),34,fc='none',ec='#977f5c',lw=1.5,ls=':'))
    for row,color in zip(rows,['#247886','#d27837']):
        p=np.array(row['points'])
        ax.plot(p[:,0],p[:,1],color=color,lw=2.6,label='ground' if row['name'].endswith('GND') else '5 V')
    ax.set(xlim=(65,307),ylim=(179,80),aspect='equal',xlabel='X / mm',ylabel='Y / mm')
    ax.set_title(title,loc='left',fontsize=15,fontweight='bold')
    ax.grid(alpha=.14);ax.legend(loc='lower left',frameon=False,ncol=2)
axs[1].annotate('local crossover',(274,113),(223,91),arrowprops={'arrowstyle':'->'},fontsize=10)
axs[1].scatter([130,225],[105.5,105.5],marker='s',s=32,color='#446955')
axs[1].annotate('carrier attachment tabs',(130,105.5),(81,111),arrowprops={'arrowstyle':'->'},fontsize=10)
fig.suptitle('move the USB power run out from under the trackpad',x=.06,ha='left',fontsize=20,fontweight='bold')
fig.text(.08,.04,'Wire centerlines from the saved paths. Connector positions stay fixed. CAD and physical qualification are separate.',fontsize=10)
fig.subplots_adjust(left=.07,right=.97,top=.9,bottom=.11,hspace=.31)
fig.savefig(HERE/'views/usb-path-comparison.png',dpi=145)
plt.close(fig)
