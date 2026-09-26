"""Shared UNG analytics/ML primitives.

Small dependency-free reference implementations for deterministic analytics and
model-selection metadata. Large training workloads may delegate to specialized
libraries/services while preserving this common contract.
"""
import math, random
from collections import Counter, defaultdict

EPS=1e-12
def mean(x): return sum(x)/len(x) if x else 0.0
def variance(x):
    m=mean(x); return mean([(v-m)**2 for v in x])
def stddev(x): return math.sqrt(variance(x))
def z_scores(x):
    m,s=mean(x),stddev(x); return [(v-m)/s if s>EPS else 0.0 for v in x]
def mse(y,p): return mean([(a-b)**2 for a,b in zip(y,p)])
def mae(y,p): return mean([abs(a-b) for a,b in zip(y,p)])
def r2(y,p):
    den=sum((v-mean(y))**2 for v in y); return 1-sum((a-b)**2 for a,b in zip(y,p))/den if den>EPS else 0.0
def sigmoid(z): return 1/(1+math.exp(-max(-709,min(709,z))))
def softmax(z):
    m=max(z);e=[math.exp(v-m) for v in z];s=sum(e);return [v/s for v in e]
def relu(x): return max(0.0,x)
def cosine_similarity(a,b):
    d=math.sqrt(sum(x*x for x in a)*sum(y*y for y in b)); return sum(x*y for x,y in zip(a,b))/d if d>EPS else 0.0
def euclidean(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def manhattan(a,b): return sum(abs(x-y) for x,y in zip(a,b))
def entropy(probs): return -sum(p*math.log(p) for p in probs if p>0)
def gini(labels):
    n=len(labels);return 1-sum((c/n)**2 for c in Counter(labels).values()) if n else 0.0
def kl_divergence(p,q):
    return sum(a*math.log(a/max(b,EPS)) for a,b in zip(p,q) if a>0)
def log_loss(y,p):
    return -mean([a*math.log(max(EPS,min(1-EPS,b)))+(1-a)*math.log(max(EPS,min(1-EPS,1-b))) for a,b in zip(y,p)])
def classification_metrics(y,p):
    tp=sum(a==1 and b==1 for a,b in zip(y,p));tn=sum(a==0 and b==0 for a,b in zip(y,p));fp=sum(a==0 and b==1 for a,b in zip(y,p));fn=sum(a==1 and b==0 for a,b in zip(y,p))
    precision=tp/max(1,tp+fp);recall=tp/max(1,tp+fn);f1=2*precision*recall/max(EPS,precision+recall)
    return {"accuracy":(tp+tn)/max(1,len(y)),"precision":precision,"recall":recall,"f1":f1,"confusion":{"tp":tp,"tn":tn,"fp":fp,"fn":fn}}
def correlation(x,y):
    mx,my=mean(x),mean(y);num=sum((a-mx)*(b-my) for a,b in zip(x,y));den=math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y));return num/den if den>EPS else 0.0

class GaussianNaiveBayes:
    def fit(self,X,y):
        self.classes=sorted(set(y));self.stats={}
        for c in self.classes:
            rows=[r for r,t in zip(X,y) if t==c];cols=list(zip(*rows))
            self.stats[c]=(len(rows)/len(X),[(mean(v),max(variance(v),EPS)) for v in cols])
        return self
    def predict_proba_one(self,x):
        logs={}
        for c,(prior,stats) in self.stats.items():
            s=math.log(prior)
            for v,(m,var) in zip(x,stats):s+=-.5*math.log(2*math.pi*var)-(v-m)**2/(2*var)
            logs[c]=s
        m=max(logs.values());z=sum(math.exp(v-m) for v in logs.values());return {c:math.exp(v-m)/z for c,v in logs.items()}
    def predict(self,X): return [max(self.predict_proba_one(x),key=self.predict_proba_one(x).get) for x in X]

class KNN:
    def __init__(self,k=5,distance="euclidean"): self.k=k;self.distance=distance
    def fit(self,X,y): self.X=list(X);self.y=list(y);return self
    def predict(self,X):
        d=manhattan if self.distance=="manhattan" else euclidean
        return [Counter(t for _,t in sorted((d(x,r),t) for r,t in zip(self.X,self.y))[:self.k]).most_common(1)[0][0] for x in X]

def kmeans(X,k,iterations=100,seed=0):
    if k<1 or k>len(X): raise ValueError("invalid k")
    rng=random.Random(seed);cent=[list(v) for v in rng.sample(list(X),k)]
    labels=[]
    for _ in range(iterations):
        labels=[min(range(k),key=lambda j:euclidean(x,cent[j])) for x in X]
        new=[]
        for j in range(k):
            rows=[x for x,l in zip(X,labels) if l==j]
            new.append([mean(c) for c in zip(*rows)] if rows else cent[j])
        if new==cent:break
        cent=new
    return {"centroids":cent,"labels":labels}

def gradient_descent(theta,gradient,lr=.01,steps=100,momentum=0.0):
    t=list(theta);v=[0.0]*len(t)
    for _ in range(steps):
        g=gradient(t);v=[momentum*a+(1-momentum)*b for a,b in zip(v,g)];t=[a-lr*b for a,b in zip(t,v)]
    return t

class Adam:
    def __init__(self,lr=.001,b1=.9,b2=.999,eps=1e-8):self.lr=lr;self.b1=b1;self.b2=b2;self.eps=eps;self.m=[];self.v=[];self.t=0
    def step(self,params,grads):
        if not self.m:self.m=[0.0]*len(params);self.v=[0.0]*len(params)
        self.t+=1;out=[]
        for i,(p,g) in enumerate(zip(params,grads)):
            self.m[i]=self.b1*self.m[i]+(1-self.b1)*g;self.v[i]=self.b2*self.v[i]+(1-self.b2)*g*g
            mh=self.m[i]/(1-self.b1**self.t);vh=self.v[i]/(1-self.b2**self.t);out.append(p-self.lr*mh/(math.sqrt(vh)+self.eps))
        return out

MODEL_CATALOG={
"linear_regression":{"task":["regression"],"scale_sensitive":False,"interpretable":True},
"logistic_regression":{"task":["classification"],"scale_sensitive":True,"interpretable":True},
"decision_tree":{"task":["classification","regression"],"nonlinear":True,"interpretable":True},
"random_forest":{"task":["classification","regression"],"ensemble":True,"nonlinear":True},
"gradient_boosting":{"task":["classification","regression"],"ensemble":True,"sequential":True,"nonlinear":True},
"naive_bayes":{"task":["classification"],"fast":True,"assumption":"conditional feature independence"},
"knn":{"task":["classification","regression"],"scale_sensitive":True,"local":True},
"svm":{"task":["classification","regression","outlier"],"scale_sensitive":True,"kernels":["linear","polynomial","rbf"]},
"kmeans":{"task":["clustering"],"scale_sensitive":True},
"pca":{"task":["dimensionality_reduction"],"scale_sensitive":True},
"svd":{"task":["factorization","dimensionality_reduction"]},
"neural_network":{"task":["classification","regression"],"nonlinear":True},
"autoencoder":{"task":["representation","anomaly_detection"]},
"transformer":{"task":["sequence","attention"]},
"reinforcement_learning":{"task":["control","sequential_decision"]},
"gan":{"task":["generative"],"training":"adversarial"}
}
