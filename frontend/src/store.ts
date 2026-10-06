import {create} from 'zustand';
import type {Telemetry} from './types';
type State={live:Telemetry|null;current:Telemetry|null;history:Telemetry[];connection:string;recording:string|null;recordPaused:boolean;simConnected:boolean;replay:boolean;receive:(t:Telemetry)=>void;display:(t:Telemetry)=>void;setReplay:(v:boolean)=>void;clear:()=>void};
export const useTelemetry=create<State>((set)=>({live:null,current:null,history:[],connection:'CONNECTING',recording:null,recordPaused:false,simConnected:true,replay:false,
receive:t=>set(s=>s.replay?{live:t}:{live:t,current:t,history:[...(s.current && t.sequence<s.current.sequence?[]:s.history),t].slice(-6000)}),
display:t=>set(s=>({current:t,history:[...(s.current&&t.sim_time<s.current.sim_time?[]:s.history),t].slice(-6000)})),
setReplay:v=>set(s=>({replay:v,current:v?s.current:s.live,history:[]})),clear:()=>set({history:[]})}));
export function connectTelemetry(){let socket:WebSocket;let timer:number;let disposed=false;let retry=0;let last=Date.now();
 const connect=()=>{useTelemetry.setState({connection:retry?'RECONNECTING':'CONNECTING'});socket=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws/telemetry`);
 socket.onopen=()=>{socket.send(JSON.stringify({api_key:sessionStorage.getItem('api_key')||''}));retry=0;last=Date.now()};
 socket.onmessage=event=>{try{const message=JSON.parse(event.data);last=Date.now();if(message.type==='telemetry'){if(!message.data?.position||!Number.isFinite(message.data.sim_time))return;useTelemetry.setState({connection:'CONNECTED',recording:message.recording,recordPaused:message.record_paused,simConnected:message.sim_connected});useTelemetry.getState().receive(message.data)}}catch{useTelemetry.setState({connection:'DATA ERROR'})}};
 socket.onclose=()=>{if(disposed)return;useTelemetry.setState({connection:'DISCONNECTED'});timer=window.setTimeout(connect,Math.min(10000,500*2**retry++))};socket.onerror=()=>socket.close();};
 connect();const heartbeat=window.setInterval(()=>{if(socket.readyState===WebSocket.OPEN){if(Date.now()-last>12000)socket.close();else socket.send(JSON.stringify({type:'ping'}))}},5000);
 return()=>{disposed=true;clearTimeout(timer);clearInterval(heartbeat);socket.close()};
}
