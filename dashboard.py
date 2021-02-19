"""
A python dash dashboard for
our geiger counter dataviz project
"""
import datetime
from datetime import date
from dateutil import tz
import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go


external_stylesheets = [
    {
        "href": "https://fonts.googleapis.com/css2?"
        "family=Lato:wght@400;700&display=swap",
        "rel": "stylesheet",
    },
]
app = dash.Dash(
    __name__,
    requests_pathname_prefix="/dashboard/",
    external_stylesheets=external_stylesheets,
)


def build_app_from_data(
    get_dataframe_callback, get_latest_callback, all_data_rolling_avg_callback
):
    """
    Initialise the dash app using our data
    """
    all_data = all_data_rolling_avg_callback()
    if all_data is not None:
        all_data_fig = px.scatter(
            all_data,
            x="time",
            y="usv",
            title="usv per hour - Rolling mean over all data",
        )
    else:
        all_data_fig = None
    
    app.layout = html.Div(
        children=[
            html.Div(
                children=[
                    html.H1(
                        children="GMC-320 Geiger Counter Acquisition Dashboard",
                        className="header-title",
                    ),
                    dcc.Interval(
                        id="periodic-refresh",
                        interval=5000,  # in milliseconds
                    ),
                    html.P(
                        children="This dashboard displays the last 24 hours"
                        " of data from our Wifi GMC-320 located in the center of Toulouse, France."
                        " Auto-Refresh every 5 seconds.",
                        className="header-description",
                    ),
                    html.A(
                        href="https://github.com/colon3ltocard/pygeiger",
                        children="Source Code on github",
                        className="header-code-link",
                    ),
                    html.P(
                        children="Sensor Status: Unknown",
                        className="header-status",
                        id="sensor-status",
                    ),
                ],
                className="header",
            ),
            html.Div(children=[dcc.Graph(id="cpm-graph")], className="card"),
            html.Div(
                children=[dcc.Graph(id="all-graph", figure=all_data_fig)],
                className="card",
            ),
        ]
    )

    @app.callback(
        Output("cpm-graph", "figure"), Input("periodic-refresh", "n_intervals")
    )
    def draw_acpm(n):
        """
        Callback refreshing the acpm graph every time the periodic-refresh kicks in.
        """
        df = get_dataframe_callback()
        if len(df):
            acpm = go.Scatter(
                x=df.time,
                y=df.acpm,
                name="acpm",
                mode="lines",
            )
            cpm = go.Scatter(
                x=df.time,
                y=df.cpm,
                name="cpm",
                mode="markers",
            )
            data = [acpm, cpm]
            layout = go.Layout(
                yaxis=dict(
                    domain=[0, 1]
                ),
                title="(Averaged) ACPM and CPM (counts per minute) for last 24 hours",
                legend=dict(
                    traceorder="reversed"
                ),
            )
            return go.Figure(data=data, layout=layout)
        else:
            None

    @app.callback(
        Output("sensor-status", "children"), Input("periodic-refresh", "n_intervals")
    )
    def update_status(n):
        """
        Callback updating the sensor status.
        """
        latest = get_latest_callback()
        if len(latest):
            latest = latest.time[0].replace(tzinfo=tz.UTC)
            n = datetime.datetime.now(tz=tz.UTC)

            if latest < (n - datetime.timedelta(hours=24)):
                return f"Sensor Status: OFFLINE (last measurement was on {latest:%B %d, %Y at %H:%m} UTC)"
            else:
                return f"Sensor Status: ONLINE (last measurement was on {latest:%B %d, %Y at %H:%M} UTC)"
        else:
            return "Sensor Status: OFFLINE. No data in database."

    app.title = "GMC-320 data monitoring on Heroku !"
    return app
