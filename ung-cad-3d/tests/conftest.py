import io
import sys
from pathlib import Path

import pytest
import trimesh

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def stl_bytes(mesh):
    buf = io.BytesIO()
    mesh.export(buf, file_type="stl")
    return buf.getvalue()


def box(x, y, z, center=(0.0, 0.0, None)):
    m = trimesh.creation.box(extents=[x, y, z])
    cz = z / 2 if center[2] is None else center[2]
    m.apply_translation([center[0], center[1], cz])
    return m


@pytest.fixture
def app_dir():
    return APP_DIR
