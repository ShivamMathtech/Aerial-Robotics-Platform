import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'e2e',workers:1,use:{baseURL:'http://127.0.0.1:5173',headless:true,viewport:{width:1680,height:1100},screenshot:'only-on-failure'},webServer:{command:'npm run dev',url:'http://127.0.0.1:5173',reuseExistingServer:true},timeout:45000});
