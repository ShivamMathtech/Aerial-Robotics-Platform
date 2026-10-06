import {describe,it,expect,beforeEach} from 'vitest';
import {useTelemetry} from './store';
import {flatten} from './services';
import type {Telemetry} from './types';
const sample=(sequence:number)=>({sequence,sim_time:sequence*.1,position:{lat:30,lon:78,alt:124}} as Telemetry);
beforeEach(()=>useTelemetry.setState({live:null,current:null,history:[],replay:false}));
describe('Telemetry store',()=>{it('isolates replay from incoming live packets',()=>{useTelemetry.getState().receive(sample(1));useTelemetry.getState().setReplay(true);useTelemetry.getState().display(sample(50));useTelemetry.getState().receive(sample(2));expect(useTelemetry.getState().current?.sequence).toBe(50);useTelemetry.getState().setReplay(false);expect(useTelemetry.getState().current?.sequence).toBe(2)});it('bounds the history buffer',()=>{for(let i=0;i<6100;i++)useTelemetry.getState().receive(sample(i));expect(useTelemetry.getState().history).toHaveLength(6000)});it('clears trajectory on reset',()=>{useTelemetry.getState().receive(sample(100));useTelemetry.getState().receive(sample(0));expect(useTelemetry.getState().history).toHaveLength(1)});it('flattens nested telemetry for raw table',()=>{expect(flatten({position:{lat:30},armed:true})).toEqual({'position.lat':30,armed:true})})
});
