"""Batch 1 operational persistence for UNG-CAD-3D."""
import json, sqlite3
from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat()

def migrate(c: sqlite3.Connection):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS projects(
      id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,state_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS revisions(
      id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER NOT NULL,revision_no INTEGER NOT NULL,
      state_json TEXT NOT NULL,created_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id),UNIQUE(project_id,revision_no));
    CREATE TABLE IF NOT EXISTS materials(
      id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,material_type TEXT NOT NULL,
      color TEXT,remaining_g REAL,cost_per_kg REAL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS queue(
      id INTEGER PRIMARY KEY AUTOINCREMENT,job_id INTEGER,machine_id INTEGER,priority INTEGER NOT NULL DEFAULT 100,
      state TEXT NOT NULL DEFAULT 'queued',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS audit_events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,event_type TEXT NOT NULL,
      object_type TEXT,object_id TEXT,details_json TEXT,created_at TEXT NOT NULL);
    """)
    for table,col,decl in [
      ("jobs","machine_id","INTEGER"),("jobs","progress","REAL NOT NULL DEFAULT 0"),
      ("jobs","updated_at","TEXT"),("machines","state","TEXT NOT NULL DEFAULT 'offline'"),
      ("machines","last_seen_at","TEXT")]:
        cols={r[1] for r in c.execute(f"PRAGMA table_info({table})")}
        if col not in cols: c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    c.commit()

def audit(c,actor,event_type,object_type=None,object_id=None,details=None):
    c.execute("INSERT INTO audit_events(actor,event_type,object_type,object_id,details_json,created_at) VALUES(?,?,?,?,?,?)",
      (actor,event_type,object_type,str(object_id) if object_id is not None else None,json.dumps(details or {}),now()))
    c.commit()

def create_revision(c,project_id,state):
    n=c.execute("SELECT COALESCE(MAX(revision_no),0)+1 FROM revisions WHERE project_id=?",(project_id,)).fetchone()[0]
    c.execute("INSERT INTO revisions(project_id,revision_no,state_json,created_at) VALUES(?,?,?,?)",(project_id,n,json.dumps(state),now()))
    c.commit(); return n
