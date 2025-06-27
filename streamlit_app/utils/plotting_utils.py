import plotly.express as px

def plot_time_series(df, y, title):
    return px.line(df, x="timestamp", y=y, title=title)

def plot_anomaly_score(df):
    return px.line(df, x="timestamp", y="anomaly_score", title="Anomaly Score")

def plot_rul(df):
    return px.line(df, x="timestamp", y="rul", title="Remaining Useful Life")
