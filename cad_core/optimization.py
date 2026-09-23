from dataclasses import dataclass
from typing import Callable, Dict, Tuple

@dataclass
class OptimizationProblem:
    objective: Callable[[Dict[str,float]], float]
    gradient: Callable[[Dict[str,float]], Dict[str,float]]
    bounds: Dict[str, Tuple[float,float]]

class GradientDescentOptimizer:
    def __init__(self, learning_rate: float=0.01, iterations: int=100):
        if learning_rate <= 0 or iterations < 1: raise ValueError("invalid optimizer settings")
        self.learning_rate, self.iterations = learning_rate, iterations

    def solve(self, problem: OptimizationProblem, initial: Dict[str,float]):
        x=dict(initial); history=[]
        for _ in range(self.iterations):
            g=problem.gradient(x)
            for k,v in x.items():
                lo,hi=problem.bounds[k]
                x[k]=min(hi,max(lo,v-self.learning_rate*g[k]))
            history.append(problem.objective(x))
        return {"parameters":x,"objective":problem.objective(x),"history":history}
