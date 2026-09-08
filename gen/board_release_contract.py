"""The six saved boards and their current routing boundary."""
BOARD_PROJECTS = {
    'center': {'pcb':'ducktop2-center.kicad_pcb','schematic':'ducktop2.kicad_sch','copper_layers':8,'routing_state':'main routing pending','routing_complete_required':False},
    'left_io': {'pcb':'left_io/left_io.kicad_pcb','schematic':'left_io/left_io.kicad_sch','copper_layers':8,'routing_state':'main routing pending; partial USB routes exist','routing_complete_required':False},
    'right_io': {'pcb':'right_io/right_io.kicad_pcb','schematic':'right_io/right_io.kicad_sch','copper_layers':8,'routing_state':'main routing pending','routing_complete_required':False},
    'bms': {'pcb':'bms/bms.kicad_pcb','schematic':'bms/bms.kicad_sch','copper_layers':4,'routing_state':'routed protection board; corrections require closure','routing_complete_required':True},
    'keyboard': {'pcb':'keyboard/12_keyboard_daughterboard.kicad_pcb','schematic':'keyboard/12_keyboard_daughterboard.kicad_sch','copper_layers':2,'routing_state':'routed keyboard','routing_complete_required':True},
    'radio': {'pcb':'radio_daughterboard/radio_daughterboard.kicad_pcb','schematic':'radio_daughterboard/radio_daughterboard.kicad_sch','copper_layers':4,'routing_state':'radio routing pending','routing_complete_required':False},
}
