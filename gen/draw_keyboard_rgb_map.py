#!/usr/bin/env python3
"""Draw the saved LED channel assignments as a routing reference."""
from pathlib import Path
import math
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from check_release_candidate import top_level_blocks
from report_schematic_pcb_eco import field
from keyboard_rgb_contract import key_assignments, led_nets

ROOT=Path(__file__).resolve().parents[1]


def main():
    board=(ROOT/'keyboard/12_keyboard_daughterboard.kicad_pcb').read_text()
    fps={field(f,'Reference'):f for f in top_level_blocks(board,'(footprint ')}
    mapping=key_assignments(); keys=[]
    for i in range(65):
        f=fps[f'LED{320+i}'];x,y=map(float,re.search(r'\(at\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)',f).groups())
        nets={re.search(r'^\(pad "([^"]*)"',p)[1]:re.search(r'\(net (?:\d+ )?"([^"]*)"',p)[1] for p in top_level_blocks(f,'(pad ')}
        assert nets==led_nets(i),f'LED{320+i} differs from the channel map'
        keys.append(dict(index=i,x=x,y=y,key=field(fps[f'SW{320+i}'],'Value').rsplit(' ',1)[0]))
    colours=['#e05252','#347dc1','#32976b','#885bc1','#b78620','#dc6a21']
    fig,ax=plt.subplots(figsize=(16,5.1),layout='constrained')
    for slot in range(6):
        group=[k for k in keys if mapping[k['index']]['slot']==slot];connected={0}
        while len(connected)<len(group):
            _,a,b=min((math.hypot(group[a]['x']-group[b]['x'],group[a]['y']-group[b]['y']),a,b) for a in connected for b in range(len(group)) if b not in connected)
            ax.plot([group[a]['x'],group[b]['x']],[group[a]['y'],group[b]['y']],color=colours[slot],lw=1.5,alpha=.75,zorder=1);connected.add(b)
    for k in keys:
        a=mapping[k['index']];x,y=k['x'],k['y']
        ax.add_patch(Rectangle((x-7.2,y-5.2),14.4,10.4,facecolor='white',edgecolor='#d8dce3',lw=.7,zorder=2))
        ax.scatter([x],[y],s=28,color=colours[a['slot']],zorder=3)
        ax.text(x,y-2.7,k['key'],fontsize=6.5,ha='center',va='center',zorder=4)
        ax.text(x+4.8,y+3.4,str(a['bank']),fontsize=6.5,ha='center',color='#565d68',zorder=4)
    ax.set_title('keyboard RGB routing map',loc='left',fontsize=16,fontweight='bold')
    ax.set_xlim(min(k['x'] for k in keys)-10,max(k['x'] for k in keys)+10)
    ax.set_ylim(max(k['y'] for k in keys)+9,min(k['y'] for k in keys)-9)
    ax.set_aspect('equal');ax.axis('off')
    fig.supxlabel('colours show shared R/G/B sink groups; numbers show scan banks. lines show connections, not routed copper.',fontsize=9)
    fig.savefig(ROOT/'keyboard/images/rgb-routing-map.png',dpi=140)


if __name__=='__main__':main()
