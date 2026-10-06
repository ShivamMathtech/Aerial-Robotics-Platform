import math
from .schemas import Settings
from .simulator import SCENARIOS, MODES

def validate_command(sim, command):
    kind,value=command.type,command.value
    if kind=='SET_MODE' and value not in MODES: return 'Unknown flight mode'
    if kind=='SET_SCENARIO' and value not in SCENARIOS: return 'Unknown scenario'
    if kind=='SET_CONTROL':
        if not isinstance(value,dict) or not value: return 'Provide control values'
        for key,val in value.items():
            if key not in ('throttle','yaw','pitch','roll'): return 'Unknown control'
            if not math.isfinite(val) or not (0 if key=='throttle' else -100)<=val<=100: return 'Control outside valid range'
        if not sim.armed: return 'Arm the simulated vehicle before changing controls'
    if sim.state=='EMERGENCY' and kind not in ('RESET','PAUSE','RESUME'): return 'Emergency latched: reset required'
    if kind=='DISARM' and sim.alt>1 and sim.armed: return 'Land before disarming; emergency stop is available'
    if kind in ('RTH','LAND') and not sim.armed: return 'Vehicle must be armed'
    if kind=='RTH' and sim.satellites<6: return 'Return home requires a 3D GPS fix'
    if kind=='ARM' and sim.battery<15: return 'Battery critically low; reset the simulator'
    return None

def evaluate_alerts(t, settings: Settings, connected=True):
    rules={}
    def add(key,severity,message): rules[key]=(severity,message)
    if t.battery.percentage<15: add('battery','CRITICAL','Battery below 15%')
    elif t.battery.percentage<settings.battery_warning: add('battery','WARNING',f'Battery below {settings.battery_warning:g}%')
    if t.rssi<settings.rssi_warning: add('signal','WARNING','Telemetry signal degraded')
    if t.gps.fix=='NO FIX': add('gps','CRITICAL','GPS fix lost')
    elif t.gps.satellites<settings.gps_warning: add('gps','WARNING','Low satellite count')
    if t.packet_loss>10: add('loss','WARNING','Simulated packet loss exceeds 10%')
    if t.temperature>70: add('temperature','WARNING','Sensor temperature exceeds 70°C')
    if not connected: add('connection','CRITICAL','Simulator disconnected')
    if t.state=='EMERGENCY': add('emergency','CRITICAL','Emergency stop latched')
    if math.hypot(t.position.x,t.position.y)>500: add('geofence','WARNING','Vehicle outside 500 m visual geofence')
    return rules
