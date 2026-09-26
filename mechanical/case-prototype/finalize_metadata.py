#!/usr/bin/env python3
"""Regenerate schedule summaries, signed gravity loads and source bindings."""
import csv
import hashlib
import json
import math
from collections import Counter
from cad import HERE,ROOT
from build import CONFIG,INVENTORY


def main():
    path=HERE/'mounting-schedule.csv'
    with path.open(newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    upper=CONFIG['boards']['keyboard']['bottom_height']-4.5;fan=CONFIG['cooling']['blower'][2]
    for row in rows:
        if row['reference'].startswith('cooling-cradle-'):
            row['fastener_length_mm']=str(round(upper-fan+5.5,1))
            row['status']='low-profile head, 1.5 mm nut engagement; trim to length to clear SW3; thermal test pending'
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    counts=Counter((r['thread'],r['fastener_length_mm']) for r in rows if r['thread'] not in ['none','clips'])
    (HERE/'fastener-summary.json').write_text(json.dumps([{'thread_or_spec':k[0],'length_mm':k[1],'quantity':v,
        'note':'consult row insulation, mating part and status before selecting hardware'} for k,v in sorted(counts.items())],indent=2)+'\n')
    report=json.loads((HERE/'assembly-checks.json').read_text())
    d=report['lid_mass_and_loads'];mass=d['total_kg'];s=d['COM_distance_along_lid_mm'];h=d['COM_height_above_axis_closed_mm']
    for row in d['gravity_torque']:
        a=math.radians(row['angle_deg']);row['gravity_Nm']=mass*9.80665*(s*math.cos(a)-h*math.sin(a))/1000
    d['sign_convention']='positive means gravity tends to close; negative means gravity tends to open'
    assert next(r for r in d['gravity_torque'] if r['angle_deg']==90)['gravity_Nm']<0
    base=report['stability'];mb=base['assumed_base_kg'];yb=base['assumed_base_COM_y_mm'];yr=base['rear_foot_y_mm']
    for row in base['angles']:
        a=math.radians(row['angle_deg']);yl=CONFIG['hinges']['pivot_y']+s*math.cos(a)-h*math.sin(a)
        total=(mb*yb+mass*yl)/(mb+mass)
        row.update(combined_COM_y_mm=total,rear_margin_mm=total-yr,minimum_base_kg_against_rear_tip=max(0,mass*(yr-yl)/(yb-yr)))
    report['fastener_length_screen']={'blower_suspension_length_mm':round(upper-fan+5.5,1),
        'nut_engagement_mm':1.5,'lowest_suspension_screw_tip_height_mm':fan-3.5,
        'nearby_SW3_model_top_height_mm':12.337,'tip_to_SW3_height_difference_mm':round(fan-3.5-12.337,3),
        'status':'nominal geometry screen; actual bolt head, nut, tip and backside keyboard fit pending'}
    (HERE/'assembly-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    sources={}
    for name,row in INVENTORY.items():
        current=hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()
        assert current==row['sha256'],name+' PCB changed during the case work'
        sources[name]={'file':row['file'],'sha256':current,'unchanged':True}
    manifest={'profile':CONFIG['selected_profile'],'units':'mm','PCB_sources':sources,
              'manufacturing_ready':False,'owned_part_measurements_complete':False,
              'cad_sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')},
              'assembly_config_sha256':hashlib.sha256((HERE/'assembly.json').read_bytes()).hexdigest()}
    (HERE/'source-bindings.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('schedule lengths, fastener quantities, signed lid loads and six unchanged PCB bindings recorded')


if __name__=='__main__':main()
