export type Vec={x:number;y:number;z:number};
export interface Telemetry {type:'telemetry';vehicle_id:string;timestamp:string;sim_time:number;sequence:number;position:{lat:number;lon:number;alt:number;x:number;y:number};velocity:Vec;acceleration:Vec;gyro:Vec;orientation:{roll:number;pitch:number;yaw:number};battery:{percentage:number;voltage:number;current:number};gps:{satellites:number;fix:string;hdop:number};rssi:number;temperature:number;throttle:number;rate:number;packet_loss:number;packets_lost:number;latency:number;state:string;mode:string;armed:boolean;health:string;scenario:string;paused:boolean;detections:Detection[]}
export interface Detection {class:string;confidence:number;bbox:number[];timestamp:string;track_id:number}
export interface Alert {id:string;severity:string;message:string;timestamp:string;acknowledged:boolean;active:boolean}
export interface Mission {id:string;name:string;description:string;status:string;start_time:string;target_altitude:number;max_speed:number}
export interface Session {id:string;start_time:string;end_time:string|null;status:string;samples:number;mission_id:string|null}
export interface Settings {rate:number;speed:number;seed:number;battery_warning:number;rssi_warning:number;gps_warning:number}
export interface Waypoint {id:string;lat:number;lon:number;altitude:number}
