"""Deterministic evidence report/export model."""
from __future__ import annotations
from typing import Any,Dict,Iterable,List
import hashlib,json

def build_report(case_id:str,evidence:Iterable[Dict[str,Any]],findings:Iterable[Dict[str,Any]],
                 limitations:Iterable[str]=(),tool_versions:Dict[str,str]|None=None)->Dict[str,Any]:
    report={"case_id":case_id,"evidence":list(evidence),"findings":list(findings),
            "limitations":list(limitations),"tool_versions":dict(tool_versions or {})}
    canonical=json.dumps(report,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    report["report_sha256"]=hashlib.sha256(canonical).hexdigest()
    return report

def verify_report(report:Dict[str,Any])->bool:
    copy=dict(report); expected=copy.pop("report_sha256","")
    canonical=json.dumps(copy,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(canonical).hexdigest()==expected
