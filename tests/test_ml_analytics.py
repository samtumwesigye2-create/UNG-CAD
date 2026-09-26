import pytest
from cad_core.ml_analytics import *

def test_metrics_and_similarity():
    m=classification_metrics([0,1,1,0],[0,1,0,0]);assert m["accuracy"]==pytest.approx(.75)
    assert cosine_similarity([1,0],[1,0])==pytest.approx(1)
    assert kl_divergence([.5,.5],[.5,.5])==pytest.approx(0)

def test_naive_bayes_knn_kmeans():
    X=[[0,0],[.1,.1],[5,5],[5.1,5.1]];y=[0,0,1,1]
    assert GaussianNaiveBayes().fit(X,y).predict([[0,0],[5,5]])==[0,1]
    assert KNN(k=1).fit(X,y).predict([[.05,.05],[5.05,5.05]])==[0,1]
    assert len(kmeans(X,2,seed=1)["centroids"])==2

def test_adam_and_catalog():
    a=Adam(lr=.1);p=a.step([1.0],[1.0]);assert p[0]<1
    assert "gradient_boosting" in MODEL_CATALOG and "svm" in MODEL_CATALOG
