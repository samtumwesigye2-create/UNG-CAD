#!/usr/bin/env python3
"""
UNG-CAD Safari Bridge for FlashForge Adventurer 5M / 5M Pro.
No browser hardware APIs and no third-party Python packages.
Safari talks only to this localhost HTTP server; this process talks to the printer.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import json, socket, struct, os, time, cgi

HOST="127.0.0.1"; PORT=8765
PRINTER=None

def discover(timeout=2.0):
    global PRINTER
    probes=[("255.255.255.255",48899),("225.0.0.9",19000)]
    for addr,port in probes:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:
            s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1); s.settimeout(timeout)
            s.sendto(b"UNG-CAD", (addr,port))
            data,peer=s.recvfrom(1024)
            if len(data)>=0x94:
                name=data[:128].split(b"\0",1)[0].decode("utf-8","ignore") or "FlashForge"
                cmdport=struct.unpack(">H",data[0x84:0x86])[0] or 8899
                serial=data[0x92:].split(b"\0",1)[0].decode("ascii","ignore")
                PRINTER={"ip":peer[0],"port":cmdport,"name":name,"serial":serial}
                return PRINTER
        except Exception: pass
        finally: s.close()
    return None

def recv_until(sock, marker=b"ok", timeout=8):
    sock.settimeout(timeout); buf=b""
    end=time.time()+timeout
    while time.time()<end:
        try:
            chunk=sock.recv(4096)
            if not chunk: break
            buf+=chunk
            if marker.lower() in buf.lower(): break
        except socket.timeout: break
    return buf.decode("utf-8","ignore")

def command(cmd):
    p=PRINTER or discover()
    if not p: raise RuntimeError("AD5M not found on local network")
    with socket.create_connection((p["ip"],8899),timeout=5) as s:
        s.sendall(b"~M601 S1\r\n"); recv_until(s)
        s.sendall(("~"+cmd+"\r\n").encode()); result=recv_until(s)
        try: s.sendall(b"~M602\r\n")
        except: pass
        return result

def upload(path, start=False):
    p=PRINTER or discover()
    if not p: raise RuntimeError("AD5M not found on local network")
    size=os.path.getsize(path); name=os.path.basename(path).replace(" ","_")
    remote="0:/user/"+name
    with socket.create_connection((p["ip"],8899),timeout=8) as s:
        s.sendall(b"~M601 S1\r\n"); recv_until(s)
        s.sendall(f"~M28 {size} {remote}\r\n".encode())
        ack=recv_until(s)
        if "ok" not in ack.lower() and "received" not in ack.lower():
            raise RuntimeError("Printer rejected upload: "+ack[-300:])
        with open(path,"rb") as f:
            while True:
                b=f.read(65536)
                if not b: break
                s.sendall(b)
        s.sendall(b"~M29\r\n"); done=recv_until(s,timeout=20)
        if start:
            s.sendall(f"~M23 {remote}\r\n".encode()); started=recv_until(s,timeout=10)
        else: started=""
        try: s.sendall(b"~M602\r\n")
        except: pass
    return {"file":name,"bytes":size,"upload":done,"start":started}

INDEX=r"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>UNG-CAD Safari Printer Bridge</title>
<style>body{font:16px -apple-system,BlinkMacSystemFont,sans-serif;max-width:760px;margin:35px auto;padding:20px;background:#111;color:#eee}button,input{font:inherit;padding:12px;margin:6px;border-radius:10px}button{cursor:pointer}.ok{color:#6f6}pre{white-space:pre-wrap;background:#222;padding:14px;border-radius:10px}</style>
<h1>UNG-CAD → AD5M</h1><p id=s>Bridge ready. Detecting printer…</p>
<button onclick="detect()">Detect printer</button><button onclick="cmd('M119')">Status</button>
<hr><input id=f type=file accept=".gcode,.gx"><br>
<button onclick="upload(false)">Upload only</button><button onclick="upload(true)">Upload & Print</button>
<hr><button onclick="cmd('M25')">Pause</button><button onclick="cmd('M24')">Resume</button><button onclick="cmd('M26')">Cancel</button>
<pre id=o></pre>
<script>
const out=x=>o.textContent=typeof x==='string'?x:JSON.stringify(x,null,2);
async function api(path,opt){let r=await fetch(path,opt);let j=await r.json();if(!r.ok)throw Error(j.error||r.status);return j}
async function detect(){try{let x=await api('/api/discover');s.textContent=x.printer?'Connected: '+x.printer.name+' — '+x.printer.ip:'Printer not found';out(x)}catch(e){out(e.message)}}
async function cmd(c){try{out(await api('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:c})}))}catch(e){out(e.message)}}
async function upload(start){if(!f.files[0])return out('Choose a G-code file first.');let d=new FormData();d.append('file',f.files[0]);d.append('start',start?'1':'0');try{out('Uploading…');out(await api('/api/upload',{method:'POST',body:d}))}catch(e){out(e.message)}}
detect();
</script>"""

class Handler(BaseHTTPRequestHandler):
    def sendj(self,obj,status=200):
        b=json.dumps(obj).encode(); self.send_response(status)
        self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b)))
        self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path=="/":
            b=INDEX.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
        elif self.path=="/api/discover": self.sendj({"printer":discover()})
        else: self.sendj({"error":"not found"},404)
    def do_POST(self):
        try:
            if self.path=="/api/command":
                n=int(self.headers.get("Content-Length","0")); body=json.loads(self.rfile.read(n) or b"{}")
                allowed={"M119","M105","M27","M24","M25","M26"}
                c=body.get("command","")
                if c not in allowed: raise ValueError("command not allowed")
                self.sendj({"ok":True,"response":command(c)})
            elif self.path=="/api/upload":
                form=cgi.FieldStorage(fp=self.rfile,headers=self.headers,environ={"REQUEST_METHOD":"POST","CONTENT_TYPE":self.headers.get("Content-Type","")})
                item=form["file"]; start=form.getfirst("start","0")=="1"
                name=os.path.basename(item.filename or "print.gcode")
                if not name.lower().endswith((".gcode",".gx")): raise ValueError("G-code files only")
                tmp="/tmp/ungcad-"+str(os.getpid())+"-"+name
                with open(tmp,"wb") as f:
                    while True:
                        b=item.file.read(65536)
                        if not b: break
                        f.write(b)
                try: result=upload(tmp,start)
                finally:
                    try: os.remove(tmp)
                    except: pass
                self.sendj({"ok":True,**result})
            else: self.sendj({"error":"not found"},404)
        except Exception as e: self.sendj({"ok":False,"error":str(e)},500)
    def log_message(self,fmt,*args): print("[UNG-CAD]",fmt%args)

if __name__=="__main__":
    print(f"UNG-CAD Safari Bridge: http://{HOST}:{PORT}")
    print("Printer:",discover())
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
