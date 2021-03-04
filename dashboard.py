"""
A python dash dashboard for
our geiger counter dataviz project
"""
import datetime
from datetime import date
from dateutil import tz
import pandas as pd
import dash_leaflet as dl
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go


TOULOUSE_GEO = (43.604652, 1.444209)
SENSOR_LOC = (43.599844013541535, 1.4433743991768557)
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
    # this is for preview in social medias
    meta_tags=[
        {"property": "og:title", "content": "GMC-320 dashboard on Heroku"},
        {
            "property": "og:description",
            "content": "This page is a real-time monitoring dashboard deployed on Heroku for our GMC-320 Wi-Fi geiger counter."
            " It shows the averaged and raw counts per minutes over the last 24 hours and a subsampling of the usv/h over all the dataset",
        },
        {
            "property": "og:image",
            "content": "http://geiger.tocardise.eu/dashboard/assets/preview.png",
        },
    ],
)


def build_app_from_data(
    get_dataframe_callback, get_latest_callback, all_data_rolling_avg_callback
):
    """
    Initialise the dash app using our data
    """
    all_data = all_data_rolling_avg_callback()
    if all_data is not None:
        all_data.columns = ["day", "max acpm", "number of measurements"]
        all_data_fig = px.bar(
            all_data,
            x="day",
            y="max acpm",
            title="max acpm per day",
            color="number of measurements",
        )
    else:
        all_data_fig = None

    radicon = {
        "iconUrl": "/dashboard/assets/radiation-solid.svg",
        "iconSize": [30, 30],
        "iconAnchor": [12, 41],
        "popupAnchor": [1, -34],
        "shadowSize": [41, 41],
        "color": "orange",
    }

    map_loc = dl.Map(
        [
            dl.TileLayer(),
            dl.Marker(position=SENSOR_LOC, icon=radicon),
            dl.CircleMarker(center=SENSOR_LOC, color="blue", radius=3),
        ],
        zoom=11,
        center=TOULOUSE_GEO,
        style={"width": "100%", "height": "28vh", "margin": "auto", "display": "block"},
    )

    app.layout = html.Div(
        children=[
            html.Div(
                children=[
                    html.Div(
                        children=[map_loc],
                        className="col-3",
                    ),
                    html.Div(
                        children=[
                            html.Div(
                                children=[
                                    html.H1(
                                        children="GMC-320 Geiger Counter Acquisition Dashboard",
                                        className="header-title",
                                    ),
                                    dcc.Interval(
                                        id="periodic-refresh",
                                        interval=15000,  # in milliseconds
                                    ),
                                    html.P(
                                        children="This dashboard displays the last 24 hours"
                                        " of data from our Wi-Fi GMC-320 located in the center of Toulouse, France."
                                        " Auto-Refresh every 15 seconds.",
                                        className="header-description",
                                    ),
                                    html.Div(
                                        children=[
                                            html.A(
                                                href="https://github.com/colon3ltocard/pygeiger",
                                                children="Source Code on github",
                                                className="header-code-link",
                                            ),
                                            html.A(
                                                href="/download",
                                                children="Download all data as csv",
                                                className="header-code-link",
                                            ),
                                        ],
                                        className="row",
                                        style={
                                            "margin-left": "auto",
                                            "margin-right": "auto",
                                        },
                                    ),
                                    html.P(
                                        children="Sensor Status: Unknown",
                                        className="header-status",
                                        id="sensor-status",
                                    ),
                                ],
                                className="header",
                            ),
                        ],
                        className="col-6",
                    ),
                    html.Div(
                        children=[html.Img(src="assets/gmc320.jpg", width="88%")],
                        className="col-3",
                    ),
                ],
                className="row",
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
                mode="markers",
            )
            cpm = go.Scatter(
                x=df.time,
                y=df.cpm,
                name="cpm",
                mode="markers",
            )
            data = [acpm, cpm]
            layout = go.Layout(
                yaxis=dict(domain=[0, 1]),
                title="(Averaged) ACPM and CPM (counts per minute) for last 24 hours",
                legend=dict(traceorder="reversed"),
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

            if latest < (n - datetime.timedelta(minutes=5)):
                return f"Sensor Status: OFFLINE (last measurement was on {latest:%B %d, %Y at %H:%m} UTC)"
            else:
                return f"Sensor Status: ONLINE (last measurement was on {latest:%B %d, %Y at %H:%M} UTC)"
        else:
            return "Sensor Status: OFFLINE. No data in database."

    app.title = "GMC-320 data monitoring on Heroku !"
    return app
