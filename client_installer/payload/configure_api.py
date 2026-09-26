from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
from config import Settings,get_settings,save_settings
from api_client import test_api
class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('FULL MYSQL v7 API Configuration'); self.geometry('690x280'); self.resizable(False,False)
        s=get_settings(); self.url=tk.StringVar(value=s.api_url); self.dev=tk.StringVar(value=s.device_id); self.tok=tk.StringVar(value='')
        frm=tk.Frame(self,padx=18,pady=18); frm.pack(fill='both',expand=True)
        for i,(lab,var,secret) in enumerate([('Secure API URL',self.url,False),('Device ID',self.dev,False),('API Token',self.tok,True)]):
            tk.Label(frm,text=lab,width=16,anchor='e').grid(row=i,column=0,padx=5,pady=8); tk.Entry(frm,textvariable=var,width=60,show='*' if secret else '').grid(row=i,column=1,padx=5,pady=8)
        tk.Label(frm,text='Example URL: https://full-mysql-secure-api-xxxxx.ondigitalocean.app',fg='#555').grid(row=3,column=0,columnspan=2,pady=(2,10))
        tk.Button(frm,text='Save',width=14,command=self.save).grid(row=4,column=0,pady=10); tk.Button(frm,text='Save + Test',width=18,command=self.save_test).grid(row=4,column=1,pady=10,sticky='w')
    def save(self):
        old=get_settings(); s=Settings(api_url=self.url.get().strip(),device_id=self.dev.get().strip() or 'WORK-PC',incoming_dir=old.incoming_dir,archive_dir=old.archive_dir,failed_dir=old.failed_dir,scan_seconds=old.scan_seconds,stable_seconds=old.stable_seconds,batch_quiet_seconds=old.batch_quiet_seconds,poll_seconds=old.poll_seconds); save_settings(s,self.tok.get() or None); messagebox.showinfo('Saved','API configuration saved locally.')
    def save_test(self):
        self.save()
        try: r=test_api(); messagebox.showinfo('PASS',f"Connected to FULL MYSQL API {r.get('version')}\nDB: {r.get('database',{}).get('database')}")
        except Exception as e: messagebox.showerror('API Test Failed',str(e))
if __name__=='__main__': App().mainloop()
