#!/usr/bin/env python3
"""Export the proposed stock-pipe route with dimensions for supplier review."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Polygon,Rectangle
from shapely.geometry import LineString

from cad import HERE
from build import CONFIG
from cooling import heatpipe_path


def main():
    c=CONFIG['cooling'];points,data=heatpipe_path(c)
    longer,_=heatpipe_path(c,c['heatpipe_nominal_length_mm']+c['heatpipe_length_tolerance_mm'])
    plate=json.loads((HERE/'cooling-datums.json').read_text())
    out=HERE/'drawings';out.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(12,6.8))
    fig.set_facecolor('#f6f4ef');ax.set_facecolor('#f6f4ef')
    for name,coords,color in [('fin bank',c['fins'],'#b9c9ce'),('blower',c['blower'],'#b7bdc3')]:
        x,y,_,w,d,_=coords;ax.add_patch(Rectangle((x,y),w,d,facecolor=color,edgecolor='#596870',alpha=.55))
        ax.text(x+w/2,y+d-2 if name=='fin bank' else y+d/2,name,ha='center',va='center',fontsize=10,color='#354249')
    x,y,w,d=plate['spreader_xy_mm'];ax.add_patch(Rectangle((x,y),w,d,fill=False,edgecolor='#775436',lw=1.5))
    ax.text(x+w/2,y+d-2,'spreader',ha='center',va='bottom',color='#775436')
    width=c['heatpipe_width_mm'];wide=width+c['heatpipe_width_tolerance_mm']+2*c['heatpipe_position_allowance_mm']
    margin=c['heatpipe_position_allowance_mm']
    longer[0]=(longer[0][0]+margin,longer[0][1]);longer[-1]=(longer[-1][0]-margin,longer[-1][1])
    envelope=LineString(longer).buffer(wide/2,cap_style='flat',join_style='round')
    nominal=LineString(points).buffer(width/2,cap_style='flat',join_style='round')
    ax.add_patch(Polygon(list(envelope.exterior.coords),facecolor='#ecd8b9',edgecolor='#af936c',lw=1))
    ax.add_patch(Polygon(list(nominal.exterior.coords),facecolor='#ba6b39',edgecolor='#7e4528',lw=1))
    xx,yy=zip(*points);ax.plot(xx,yy,'--',color='#fff2dc',lw=1)
    for i,(mx,my) in enumerate(plate['cooler_mount_centers_xy_mm'],1):
        ax.add_patch(Circle((mx,my),3.25,fill=False,color='#485ca6',lw=1.4))
        ax.text(mx,my+6 if i==2 else my-4.2,f'M{i}',ha='center',va='center',color='#485ca6',fontsize=9)
    for xy,label,offset in [(points[0],'hot end (240, 55)',(8,13)),
                            (points[-1],f"cold end ({points[-1][0]:.3f}, 13)",(-3,22)),
                            (c['heatpipe_bend_start_xy'],'first tangent (202, 55)',(-12,19))]:
        ax.annotate(label,xy=xy,xytext=offset,textcoords='offset points',fontsize=9,
                    arrowprops={'arrowstyle':'-','color':'#5c5045'},ha='left' if xy==points[0] else 'right')
    ax.text(170,12,'two 60° bends\nR27 centreline',ha='center',va='center',fontsize=10)
    ax.set(xlim=(45,265),ylim=(106,0),xlabel='installed X (mm)',ylabel='installed Y (mm)')
    ax.set_aspect('equal');ax.grid(alpha=.16);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('200 mm stock heatpipe fit study',x=.08,y=.97,ha='left',fontsize=17,fontweight='bold')
    ax.set_title('ATS-HP-F7L200S65W-018   |   11.2 ±0.5 mm wide   |   3.5 ±0.5 mm thick',loc='left',fontsize=10,pad=12)
    fig.text(.08,.035,'Length: 200 ±4 mm, sealed ends retained. Pale outline includes fit space. M1-M3 are hardware reservations.\nSupplier forming approval and the processor mounting load are still needed. This is not a fabrication drawing.',fontsize=9,color='#4d5559')
    fig.subplots_adjust(left=.08,right=.96,bottom=.19,top=.86)
    fig.savefig(out/'heatpipe-route.png',dpi=170)
    fig.savefig(out/'heatpipe-route.svg')
    plt.close(fig)
    with (out/'heatpipe-centerline.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['sample','installed_x_mm','installed_y_mm','bottom_H_mm'])
        for i,(x,y) in enumerate(points):writer.writerow([i,round(x,6),round(y,6),c['heatpipe'][2]])
    print('heatpipe route drawing and centreline samples saved')


if __name__=='__main__':main()
