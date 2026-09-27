"""Dash client for the UNG-CAD Calculus-3 analysis API."""
import os
import requests
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go

API_URL=os.getenv("UNG_CALC3_API_URL","http://127.0.0.1:8000/api/v3/calculate/manifold")
app=dash.Dash(__name__,title="UNG-CAD 3D Field Map")
app.layout=html.Div(style={"fontFamily":"Segoe UI,Arial,sans-serif","padding":"25px","backgroundColor":"#f8f9fa"},children=[
 html.H2("UNG-CAD Fluid Dynamics & Surface-Load Visualizer"),
 html.P("Calculus-3 parametric manifold analysis. Preliminary load estimator; not a CFD/Navier-Stokes solution."),
 html.Div(style={"display":"flex","gap":"20px"},children=[
  html.Div(style={"flex":"1"},children=[
   html.Label("Surface Z expression"),dcc.Input(id="z",value="0.2*(u**2-v**2)",style={"width":"95%"}),
   html.Label("Free-stream velocity [X,Y,Z]",style={"display":"block","marginTop":"12px"}),dcc.Input(id="vel",value="30,0,-10",style={"width":"95%"}),
   html.Label("Characteristic length (m)",style={"display":"block","marginTop":"12px"}),dcc.Input(id="length",type="number",value=0.1,min=0.000001,style={"width":"95%"})
  ]),
  html.Div(style={"flex":"1"},children=[
   html.Label("Resolution"),dcc.Slider(id="res",min=10,max=100,step=5,value=25,marks={i:str(i) for i in range(10,101,15)}),
   html.Button("Compute & Render",id="go",n_clicks=0,style={"width":"100%","marginTop":"20px","padding":"10px"})
  ])
 ]),
 html.Div(id="status",style={"marginTop":"12px"}),
 dcc.Loading(children=dcc.Graph(id="plot",style={"height":"720px"}))
])

@app.callback(Output("plot","figure"),Output("status","children"),Input("go","n_clicks"),State("z","value"),State("vel","value"),State("length","value"),State("res","value"))
def render(_,expr_z,vel,length,res):
 try:
  velocity=[float(x.strip()) for x in vel.split(",")]
  if len(velocity)!=3: raise ValueError("velocity requires exactly 3 values")
  payload={"expr_x":"u","expr_y":"v","expr_z":expr_z,"u_min":-2,"u_max":2,"v_min":-2,"v_max":2,"density":1.225,"viscosity":1.81e-5,"velocity_xyz":velocity,"characteristic_length":float(length),"resolution":int(res)}
  r=requests.post(API_URL,json=payload,timeout=45); r.raise_for_status(); data=r.json()
  df=pd.DataFrame([{"x":n["position_xyz"][0],"y":n["position_xyz"][1],"z":n["position_xyz"][2],"fx":n["resultant_vector"][0],"fy":n["resultant_vector"][1],"fz":n["resultant_vector"][2],"p":n["pressure_estimate_pa"]} for n in data["nodes"]])
 except Exception as exc:
  return go.Figure().update_layout(title="Analysis unavailable"),f"Backend error: {exc}"
 fig=go.Figure()
 fig.add_trace(go.Mesh3d(x=df.x,y=df.y,z=df.z,opacity=.35,intensity=df.p,colorscale="Viridis",name="Parametric surface"))
 fig.add_trace(go.Cone(x=df.x,y=df.y,z=df.z,u=df.fx,v=df.fy,w=df.fz,intensity=df.p,colorscale="Turbo",sizemode="scaled",sizeref=1.5,colorbar={"title":"Pressure estimate (Pa)"},name="Estimated load vectors"))
 fig.update_layout(margin={"l":0,"r":0,"t":30,"b":0},scene={"aspectmode":"data","xaxis_title":"X","yaxis_title":"Y","zaxis_title":"Z"})
 return fig,f"{len(df)} evaluated nodes · preliminary surface-load estimate · not CFD"

if __name__=="__main__":
 app.run(debug=False,host="0.0.0.0",port=int(os.getenv("PORT","8050")))
