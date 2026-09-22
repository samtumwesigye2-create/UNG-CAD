import asyncio, json, os, tempfile, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST="127.0.0.1"
PORT=8765
BRIDGE_VERSION="2026-09-20-3"
STATE={"printer":None,"check_code":None}

def _flashforge():
    try:
        from flashforge import FlashForgeClient, FiveMClientConnectionOptions, PrinterDiscovery
        return FlashForgeClient, FiveMClientConnectionOptions, PrinterDiscovery
    except ImportError:
        raise RuntimeError("flashforge-python-api not installed — run: pip install flashforge-python-api")

async def discover():
    _, _, PrinterDiscovery = _flashforge()
    found=await PrinterDiscovery().discover()
    return [{"name":p.name,"ip":p.ip_address,"serial":p.serial_number,
             "http_port":p.event_port,"tcp_port":p.command_port}
            for p in found if p.serial_number]

async def connect(check_code):
    FlashForgeClient, FiveMClientConnectionOptions, PrinterDiscovery = _flashforge()
    found=await PrinterDiscovery().discover()
    if not found:
        raise RuntimeError("No FlashForge printer discovered on this LAN")
    p=next((x for x in found if x.serial_number),None)
    if not p:
        raise RuntimeError("Discovered printer did not report a serial number")
    opts=FiveMClientConnectionOptions(http_port=p.event_port,tcp_port=p.command_port)
    async with FlashForgeClient(p.ip_address,p.serial_number,check_code,options=opts) as c:
        try:
            info=await c.get_printer_status()
        except Exception as e:
            msg=str(e)
            if "Access code is different" in msg or "access code is different" in msg:
                raise RuntimeError("Access Code mismatch — enter the CURRENT Access Code / Check Code shown in the printer Network settings")
            raise
        if not info:
            raise RuntimeError("Printer rejected connection / Access Code")
        STATE["printer"]={
            "name":c.printer_name or p.name,
            "ip":p.ip_address,
            "serial":p.serial_number,
            "firmware":c.firmware_version,
            "http_port":p.event_port,
            "tcp_port":p.command_port
        }
        STATE["check_code"]=check_code
        return STATE["printer"]

async def print_file(path, level=True):
    FlashForgeClient, FiveMClientConnectionOptions, PrinterDiscovery = _flashforge()
    if not STATE["check_code"]:
        raise RuntimeError("Pair printer first")
    found=await PrinterDiscovery().discover()
    serial=STATE["printer"]["serial"]
    p=next((x for x in found if x.serial_number==serial),None)
    if not p:
        raise RuntimeError("Paired printer is not discoverable")
    opts=FiveMClientConnectionOptions(http_port=p.event_port,tcp_port=p.command_port)
    async with FlashForgeClient(p.ip_address,p.serial_number,STATE["check_code"],options=opts) as c:
        info=await c.get_printer_status()
        if not info:
            raise RuntimeError("Printer connection failed")
        await c.init_control()
        uploaded=await c.job_control.upload_file(path,start_print=False,level_before_print=level)
        if not uploaded:
            raise RuntimeError("Printer rejected file upload")
        started=await c.job_control.print_local_file(Path(path).name,leveling_before_print=level)
        if not started:
            raise RuntimeError("File uploaded but printer rejected explicit start command")
        return {"started":True,"file":Path(path).name,"mode":"upload_then_explicit_start"}

def list_serial_ports():
    import serial.tools.list_ports
    return [{"device":p.device,"description":p.description} for p in serial.tools.list_ports.comports()]

def send_gcode_serial(port, baud, gcode_text, progress_cb=None):
    import serial
    lines=[l for l in gcode_text.splitlines() if l.strip() and not l.strip().startswith(";")]
    with serial.Serial(port, baud, timeout=5) as ser:
        time.sleep(2)
        ser.reset_input_buffer()
        for i,line in enumerate(lines):
            ser.write((line+"\n").encode())
            deadline=time.time()+30
            while time.time()<deadline:
                resp=ser.readline().decode(errors="ignore").strip()
                if resp.lower().startswith("ok"):
                    break
                if resp.lower().startswith("error") or resp.lower().startswith("alarm"):
                    raise RuntimeError(f"Machine reported {resp} at line {i+1}: {line}")
            else:
                raise RuntimeError(f"Timed out waiting for controller acknowledgement at line {i+1}: {line}")
            if progress_cb:
                progress_cb(i+1,len(lines))
    return {"sent_lines":len(lines)}

class H(BaseHTTPRequestHandler):
    def cors(self,code=200,ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type",ctype)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Headers","Content-Type,X-Printer-ID,X-Filename,X-Level,X-Port,X-Baud")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.end_headers()

    def do_OPTIONS(self):
        self.cors(204)

    def out(self,obj,code=200):
        self.cors(code)
        self.wfile.write(json.dumps(obj).encode())

    def do_GET(self):
        try:
            if self.path=="/health":
                return self.out({"ok":True,"bridge":"UNG-CAD","version":BRIDGE_VERSION,"printer":STATE["printer"]})
            if self.path=="/discover":
                return self.out({"printers":asyncio.run(discover())})
            if self.path=="/serial/ports":
                try:
                    return self.out({"ports":list_serial_ports()})
                except ImportError:
                    return self.out({"error":"pyserial not installed — run: pip install pyserial"},500)
            return self.out({"error":"not found"},404)
        except Exception as e:
            self.out({"error":str(e)},500)

    def do_POST(self):
        try:
            if self.path=="/pair":
                n=int(self.headers.get("Content-Length","0"))
                data=json.loads(self.rfile.read(n) or b"{}")
                code=str(data.get("printer_id","")).strip()
                if not code:
                    return self.out({"error":"Printer ID required"},400)
                return self.out({"paired":True,"printer":asyncio.run(connect(code))})

            if self.path=="/print":
                name=self.headers.get("X-Filename","print.gcode")
                if not name.lower().endswith((".gcode",".gx",".3mf")):
                    return self.out({"error":"File must already be sliced (.gcode/.gx/.3mf)"},400)
                n=int(self.headers.get("Content-Length","0"))
                raw=self.rfile.read(n)
                safe_name=Path(name).name
                tmpdir=tempfile.mkdtemp(prefix="ungcad_")
                path=str(Path(tmpdir)/safe_name)
                Path(path).write_bytes(raw)
                try:
                    return self.out(asyncio.run(print_file(path,self.headers.get("X-Level","true").lower()=="true")))
                finally:
                    try:
                        os.unlink(path)
                        os.rmdir(tmpdir)
                    except Exception:
                        pass

            if self.path=="/serial/send":
                port=self.headers.get("X-Port")
                baud=int(self.headers.get("X-Baud","115200"))
                if not port:
                    return self.out({"error":"X-Port header required (e.g. /dev/ttyUSB0 or COM3)"},400)
                n=int(self.headers.get("Content-Length","0"))
                gcode_text=self.rfile.read(n).decode(errors="ignore")
                if not gcode_text.strip():
                    return self.out({"error":"Empty G-code body"},400)
                try:
                    result=send_gcode_serial(port,baud,gcode_text)
                    return self.out({"ok":True,**result})
                except ImportError:
                    return self.out({"error":"pyserial not installed — run: pip install pyserial"},500)
            return self.out({"error":"not found"},404)
        except Exception as e:
            self.out({"error":str(e)},500)

    def log_message(self,*args):
        pass

if __name__=="__main__":
    print(f"UNG-CAD bridge ready on http://{HOST}:{PORT}")
    print("Handles: FlashForge Adventurer 5M (LAN) and CNC/laser controllers (USB serial)")
    ThreadingHTTPServer((HOST,PORT),H).serve_forever()
