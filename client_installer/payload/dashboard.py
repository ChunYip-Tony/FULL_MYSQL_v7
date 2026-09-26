from __future__ import annotations
import json,os,subprocess,threading,tkinter as tk
from tkinter import messagebox,scrolledtext
from pathlib import Path
from config import APP_DIR,get_settings
from api_client import test_api
PID=APP_DIR/'agent.pid'; STATUS=APP_DIR/'agent_status.json'
def pid_running(pid):
    try:
        cp=subprocess.run(['tasklist','/FI',f'PID eq {pid}','/FO','CSV','/NH'],capture_output=True,text=True,timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)); return f'"{pid}"' in (cp.stdout or '')
    except:return False
def current_pid():
    try: p=int(PID.read_text().strip()); return p if pid_running(p) else None
    except:return None
def start_agent():
    if current_pid(): return
    exe=APP_DIR/'.venv'/'Scripts'/'pythonw.exe'; subprocess.Popen([str(exe),str(APP_DIR/'agent.py')],cwd=str(APP_DIR),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
def stop_agent():
    p=current_pid()
    if p: subprocess.run(['taskkill','/PID',str(p),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    PID.unlink(missing_ok=True)
class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('FULL MYSQL Seafood Client v7.0 — HTTPS'); self.geometry('1050x760'); self.build(); self.after(300,self.refresh); self.after(5000,self.loop)
    def build(self):
        tk.Label(self,text='🐟 FULL MYSQL Seafood Client v7.0',font=('Segoe UI',18,'bold')).pack(anchor='w',padx=14,pady=(12,2)); tk.Label(self,text='HTTPS 443 → FULL MYSQL Secure API → Managed MySQL',fg='#555').pack(anchor='w',padx=14)
        b=tk.Frame(self); b.pack(fill='x',padx=14,pady=10)
        for lab,cmd in [('Configure API',self.cfg),('Test API',self.test),('Open Incoming',self.open_in),('Start Client',self.start),('Stop Client',self.stop),('Refresh',self.refresh)]: tk.Button(b,text=lab,command=cmd,padx=8).pack(side='left',padx=(0,6))
        self.state=tk.StringVar(value='Starting…'); tk.Label(self,textvariable=self.state,font=('Segoe UI',14,'bold'),anchor='w').pack(fill='x',padx=14,pady=4)
        self.info=scrolledtext.ScrolledText(self,font=('Consolas',10),wrap='word'); self.info.pack(fill='both',expand=True,padx=14,pady=8)
    def cfg(self): subprocess.Popen([str(APP_DIR/'.venv'/'Scripts'/'python.exe'),str(APP_DIR/'configure_api.py')],cwd=str(APP_DIR))
    def test(self):
        try:r=test_api(); messagebox.showinfo('PASS',f"API {r.get('version')}\nDB {r.get('database',{}).get('database')}")
        except Exception as e: messagebox.showerror('API Test Failed',str(e))
    def open_in(self):
        p=get_settings().path(get_settings().incoming_dir); p.mkdir(exist_ok=True); os.startfile(str(p))
    def start(self): start_agent(); self.after(700,self.refresh)
    def stop(self): stop_agent(); self.refresh()
    def loop(self): self.refresh(); self.after(5000,self.loop)
    def refresh(self):
        local={}
        try: local=json.loads(STATUS.read_text(encoding='utf-8'))
        except: pass
        self.state.set(f"Client: {'RUNNING' if current_pid() else 'STOPPED'} | {local.get('state','—')}")
        lines=['LOCAL STATUS',json.dumps(local,indent=2,ensure_ascii=False,default=str),'']
        try:
            r=test_api(); lines += ['SERVER STATUS',json.dumps(r,indent=2,ensure_ascii=False,default=str)]
        except Exception as e: lines += ['SERVER STATUS',f'ERROR: {e}']
        self.info.delete('1.0','end'); self.info.insert('1.0','\n'.join(lines))
if __name__=='__main__': App().mainloop()
