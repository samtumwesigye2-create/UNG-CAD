import os
import re
import sys

TEMP_DROP_OFFSET = 10
SPEED_CLAMP_MM_S = 20
MIN_PLA_TEMP_C = 190

OVERHANG_MARKERS = (";TYPE:Overhang perimeter", ";TYPE:Bridge")
E_PARAM = re.compile(r"\bE[-+]?(?:\d+(?:\.\d*)?|\.\d+)\b")
F_PARAM = re.compile(r"\bF[-+]?(?:\d+(?:\.\d*)?|\.\d+)\b")
S_PARAM = re.compile(r"\bS(\d+(?:\.\d*)?)\b")

def process_orcaslicer_pla_overhang_cross_platform(input_file_path, temp_drop_c=TEMP_DROP_OFFSET, speed_mm_s=SPEED_CLAMP_MM_S):
    output_file_path = input_file_path + ".tmp"
    inside = False
    normal_fan = 255
    normal_temp = None
    feedrate = int(speed_mm_s * 60)

    try:
        with open(input_file_path, "r", encoding="utf-8") as infile, open(output_file_path, "w", encoding="utf-8", newline="") as outfile:
            for line in infile:
                stripped = line.strip()

                if not inside and (stripped.startswith("M104") or stripped.startswith("M109")):
                    m = S_PARAM.search(stripped)
                    if m:
                        normal_temp = float(m.group(1))

                if not inside and stripped.startswith("M106"):
                    m = S_PARAM.search(stripped)
                    if m:
                        normal_fan = max(0, min(255, int(float(m.group(1)))))

                is_overhang_marker = any(marker in stripped for marker in OVERHANG_MARKERS)

                if is_overhang_marker:
                    outfile.write(line)
                    if not inside:
                        inside = True
                        outfile.write("M106 S255 ; UNG-CAD PLA Overhang Max Fan\n")
                        if normal_temp is not None and temp_drop_c > 0:
                            target = max(MIN_PLA_TEMP_C, normal_temp - temp_drop_c)
                            outfile.write(f"M104 S{target:g} ; UNG-CAD bounded PLA overhang temperature\n")
                    continue

                if stripped.startswith(";TYPE:") and inside:
                    inside = False
                    outfile.write(f"M106 S{normal_fan} ; UNG-CAD Restore Baseline PLA Cooling\n")
                    if normal_temp is not None and temp_drop_c > 0:
                        outfile.write(f"M104 S{normal_temp:g} ; UNG-CAD Restore Original Temp\n")

                if inside and stripped.startswith("G1") and E_PARAM.search(stripped):
                    if F_PARAM.search(stripped):
                        stripped = F_PARAM.sub(f"F{feedrate}", stripped, count=1)
                    else:
                        stripped += f" F{feedrate}"
                    line = stripped + f" ; UNG-CAD PLA Speed Clamp ({speed_mm_s:g}mm/s)\n"

                outfile.write(line)

            if inside:
                outfile.write(f"M106 S{normal_fan} ; UNG-CAD Restore Baseline PLA Cooling at EOF\n")
                if normal_temp is not None and temp_drop_c > 0:
                    outfile.write(f"M104 S{normal_temp:g} ; UNG-CAD Restore Original Temp at EOF\n")

        os.replace(output_file_path, input_file_path)
    except Exception:
        try:
            if os.path.exists(output_file_path):
                os.remove(output_file_path)
        finally:
            raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: ung_overhang_fix.py <gcode-file>")
    process_orcaslicer_pla_overhang_cross_platform(sys.argv[1])
