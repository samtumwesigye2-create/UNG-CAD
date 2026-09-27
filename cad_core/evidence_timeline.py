"""Timeline and cross-artifact correlation for authorized evidence."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re

@dataclass(frozen=True)
class TimelineEvent:
    timestamp: str
    artifact_type: str
    source_ref: str
    observed: Dict[str, Any]
    confidence: float = 1.0

    def dt(self) -> datetime:
        value=self.timestamp.replace("Z","+00:00")
        d=datetime.fromisoformat(value)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

def build_timeline(events: Iterable[TimelineEvent]) -> List[TimelineEvent]:
    return sorted(events,key=lambda e:(e.dt(),e.source_ref,e.artifact_type))

def _tokens(v: Any) -> set[str]:
    if v is None: return set()
    if isinstance(v,(list,tuple,set)): return set().union(*(_tokens(x) for x in v)) if v else set()
    if isinstance(v,dict): return set().union(*(_tokens(x) for x in v.values())) if v else set()
    return {x.lower() for x in re.findall(r"[A-Za-z0-9@._+:-]{3,}",str(v))}

def correlation_score(a: TimelineEvent,b: TimelineEvent,window_seconds: int=300) -> Tuple[float,List[str]]:
    reasons: List[str]=[]
    shared=_tokens(a.observed)&_tokens(b.observed)
    delta=abs((a.dt()-b.dt()).total_seconds())
    score=0.0
    if shared:
        score+=min(0.65,0.15+0.10*len(shared)); reasons.append("shared-identifiers")
    if delta<=window_seconds:
        score+=0.25*(1.0-delta/max(window_seconds,1)); reasons.append("temporal-proximity")
    if a.source_ref==b.source_ref:
        score+=0.10; reasons.append("same-source")
    return min(score,1.0),reasons

def correlate(events: Iterable[TimelineEvent], threshold: float=0.25,
              window_seconds: int=300) -> List[Dict[str,Any]]:
    ordered=build_timeline(events); out=[]
    for i,a in enumerate(ordered):
        for b in ordered[i+1:]:
            delta=(b.dt()-a.dt()).total_seconds()
            if delta>window_seconds and not (_tokens(a.observed)&_tokens(b.observed)):
                continue
            score,reasons=correlation_score(a,b,window_seconds)
            if score>=threshold:
                out.append({"left":a.source_ref,"right":b.source_ref,
                            "score":round(score,6),"reasons":reasons,
                            "time_delta_seconds":delta})
    return sorted(out,key=lambda x:(-x["score"],x["left"],x["right"]))

def reconstruct_threads(events: Iterable[TimelineEvent]) -> Dict[str,List[TimelineEvent]]:
    threads: Dict[str,List[TimelineEvent]]={}
    for e in build_timeline(events):
        key=str(e.observed.get("thread_id") or e.observed.get("conversation_id") or "").strip()
        if key: threads.setdefault(key,[]).append(e)
    return threads
