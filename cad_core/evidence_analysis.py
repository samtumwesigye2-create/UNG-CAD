"""Search, relationship graph, anomaly and media-metadata helpers for authorized evidence."""
from __future__ import annotations
from collections import Counter,defaultdict
from typing import Any,Dict,Iterable,List
import hashlib,math,re

def _text(v:Any)->str:
    if isinstance(v,dict): return " ".join(_text(x) for x in v.values())
    if isinstance(v,(list,tuple,set)): return " ".join(_text(x) for x in v)
    return "" if v is None else str(v)

def build_search_index(artifacts:Iterable[Dict[str,Any]])->Dict[str,List[str]]:
    idx=defaultdict(list)
    for a in artifacts:
        ref=str(a["source_ref"])
        for t in set(re.findall(r"[a-z0-9@._+:-]{2,}",_text(a.get("observed",{})).lower())):
            idx[t].append(ref)
    return {k:sorted(set(v)) for k,v in idx.items()}

def search(index:Dict[str,List[str]],query:str)->List[str]:
    terms=re.findall(r"[a-z0-9@._+:-]{2,}",query.lower())
    if not terms:return []
    sets=[set(index.get(t,[])) for t in terms]
    return sorted(set.intersection(*sets)) if sets else []

def relationship_graph(artifacts:Iterable[Dict[str,Any]])->Dict[str,Any]:
    owners=defaultdict(set); nodes=set()
    for a in artifacts:
        ref=str(a["source_ref"]); nodes.add(ref)
        for token in set(re.findall(r"[A-Za-z0-9@._+:-]{3,}",_text(a.get("observed",{})))):
            owners[token.lower()].add(ref)
    edges=[]
    for token,refs in owners.items():
        refs=sorted(refs)
        for i,a in enumerate(refs):
            for b in refs[i+1:]: edges.append({"source":a,"target":b,"basis":token})
    return {"nodes":[{"id":x} for x in sorted(nodes)],"edges":edges}

def frequency_anomalies(values:Iterable[str],z_threshold:float=2.0)->List[Dict[str,Any]]:
    counts=Counter(values)
    if len(counts)<2:return []
    xs=list(counts.values()); mean=sum(xs)/len(xs)
    sd=math.sqrt(sum((x-mean)**2 for x in xs)/len(xs))
    if sd==0:return []
    return [{"value":k,"count":v,"z":(v-mean)/sd} for k,v in counts.items() if abs((v-mean)/sd)>=z_threshold]

def media_record(data:bytes,metadata:Dict[str,Any]|None=None)->Dict[str,Any]:
    return {"sha256":hashlib.sha256(data).hexdigest(),"size_bytes":len(data),"metadata":dict(metadata or {})}
