import math

def _paths_from_shapes(shapes, scale):
    paths=[]
    for s in shapes:
        t=s.get("t")
        if t in ("label","dim"):
            continue
        if t=="line":
            paths.append([(s["a"]["x"]*scale,s["a"]["y"]*scale),(s["b"]["x"]*scale,s["b"]["y"]*scale)])
        elif t=="rect":
            a,b=s["a"],s["b"]; x1,y1=a["x"]*scale,a["y"]*scale; x2,y2=b["x"]*scale,b["y"]*scale
            paths.append([(x1,y1),(x2,y1),(x2,y2),(x1,y2),(x1,y1)])
        elif t=="circle":
            a,b=s["a"],s["b"]; cx,cy=a["x"]*scale,a["y"]*scale
            r=math.hypot(b["x"]-a["x"],b["y"]-a["y"])*scale
            n=max(24,int(2*math.pi*r/2))
            paths.append([(cx+r*math.cos(2*math.pi*i/n),cy+r*math.sin(2*math.pi*i/n)) for i in range(n+1)])
    return paths

def _path_length(path):
    return sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(path,path[1:]))

def generate_gcode(paths, settings):
    mode=settings.get("mode","laser")
    feed=float(settings.get("feed_rate",800))
    plunge=float(settings.get("plunge_rate",200))
    safe_z=float(settings.get("safe_z",5))
    depth_pass=abs(float(settings.get("cut_depth_per_pass",1)))
    total_depth=abs(float(settings.get("total_depth",1)))
    spindle=int(settings.get("spindle_speed",12000))
    laser_pct=max(0,min(100,float(settings.get("laser_power_percent",80))))
    lines=["; UNG-CAD CNC/Laser generated G-code","G90","G21"]
    passes=1 if mode=="laser" else max(1,math.ceil(total_depth/depth_pass))
    if mode=="laser":
        lines += ["M4",f"S{int(1000*laser_pct/100)}"]
    else:
        lines += [f"G0 Z{safe_z:.3f}",f"M3 S{spindle}"]
    for pnum in range(1,passes+1):
        z=-min(total_depth,pnum*depth_pass)
        for path in paths:
            if len(path)<2: continue
            x0,y0=path[0]
            if mode=="cnc":
                lines += [f"G0 Z{safe_z:.3f}",f"G0 X{x0:.3f} Y{y0:.3f}",f"G1 Z{z:.3f} F{plunge:.1f}"]
            else:
                lines.append(f"G0 X{x0:.3f} Y{y0:.3f}")
            for x,y in path[1:]:
                lines.append(f"G1 X{x:.3f} Y{y:.3f} F{feed:.1f}")
    if mode=="cnc": lines += [f"G0 Z{safe_z:.3f}","M5"]
    else: lines += ["M5"]
    lines += ["G0 X0 Y0","M2"]
    return "\n".join(lines)+"\n",passes

def slice_shapes_to_gcode(shapes, settings):
    scale=float(settings.get("scale_mm_per_px",1))
    paths=_paths_from_shapes(shapes,scale)
    if not paths:
        raise ValueError("No machinable geometry found (labels and dimensions are not toolpaths)")
    gcode,passes=generate_gcode(paths,settings)
    feed=max(1,float(settings.get("feed_rate",800)))
    total_mm=sum(_path_length(p) for p in paths)*passes
    est_seconds=round(total_mm/feed*60,1)
    return gcode,len(paths),est_seconds
