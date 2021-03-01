"""
A webserver which receives and processes GMC 320+V5 POST requests
and serves the aggregated data.
"""
import os
import socket
import logging
import datetime
from contextlib import contextmanager
import asyncio
import aiohttp
import pandas as pd
import psycopg2
import sqlite3
from fastapi import FastAPI, Request, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse
from tortoise.contrib.fastapi import register_tortoise
from starlette.middleware.wsgi import WSGIMiddleware
from models import GeigerCounter, Measurement, ApiMeasurement
from dashboard import build_app_from_data


TORTOISE_ORM = {
    "connections": {"default": os.environ["DATABASE_URL"]},
    "apps": {"models": {"models": ["models"], "default_connection": "default"}},
}
HOME = os.environ["HOME_HOSTNAME"]
FORWARD_TO_GMC = os.environ.get("FORWARD_TO_GMC", False)
logger = logging.getLogger(__name__)
app = FastAPI()
register_tortoise(app, config=TORTOISE_ORM, generate_schemas=True)


def protect(request: Request):
    """
    Our sensor is behind a dyndns ISP box.
    We all data injection only from the resolved IP
    and localhost.
    """
    if request.client.host not in (
        "127.0.0.1",
        socket.gethostbyname(HOME),
    ):
        raise HTTPException(status_code=404, detail="Forbidden")


@app.get("/upload", dependencies=[Depends(protect)])
async def upload_data(
    request: Request,
    AID: str = Query(..., description="User ID"),
    GID: str = Query(..., description="Geiger Counter ID"),
    CPM: int = Query(..., description="Counts per Minute"),
    ACPM: float = Query(..., description="Average counts per minute"),
    uSV: float = Query(..., description="Value in Micro sieverts."),
):
    """
    Stores the datapoint defined by the request Query arguments.
    """
    if FORWARD_TO_GMC:
        # we forward the data to geiger map website
        try:
            async with aiohttp.ClientSession() as session:
                params = {"AID": AID, "GID": GID, "CPM": CPM, "ACPM": ACPM, "uSV": uSV}
                async with session.get(
                    "http://www.gmcmap.com/log2.asp", params=params, timeout=1.0
                ) as response:
                    logger.debug(f"Response from gmcmap: {response.status}")
        except Exception:
            logger.warning("Error forwarding request to geigermap", exc_info=True)

    gc, _ = await GeigerCounter.get_or_create(owner_id=AID, geigerc_id=GID)
    await gc.save()
    m = await Measurement.create(counter=gc, cpm=CPM, acpm=ACPM, usv=uSV)
    await m.save()

    # we delete the oldest entries if we are above 9000 lines(heroku free limit is at 10k)
    count = await Measurement.all().count()
    if count > 9000:
        r = await Measurement.all().order_by("time").limit(100)
        r = r[-1]
        await Measurement.filter(time__lte=r.time).delete()

    return HTMLResponse("OK.ERR0")


def _get_connection():
    db_conn = TORTOISE_ORM["connections"]["default"]
    if db_conn.startswith("sqlite"):
        c = sqlite3.connect(db_conn.strip("sqlite://"))
    else:
        c = psycopg2.connect(db_conn)
    return c


def get_connection():
    """
    Returns the appropriate low level db connection.
    Use this generator with fastapi Depends(...)
    """
    try:
        c = _get_connection()
        yield c
    finally:
        c.close()


safe_conn = contextmanager(get_connection)


@app.get("/download")
def download_all(conn=Depends(get_connection)) -> StreamingResponse:
    """
    Downloads all data in csv format. Uses chunking to limit memory peak.
    """

    def data_generator():
        for index, chunk in enumerate(
            pd.read_sql(
                'select * from measurement ORDER BY "time" ASC', conn, chunksize=1000
            )
        ):
            if index == 0:
                yield chunk.to_csv(index=False, header=True)
            else:
                yield chunk.to_csv(index=False, header=False)

    return StreamingResponse(
        data_generator(),
        media_type="text/csv",
        headers={"content-disposition": f"attachment; filename=geiger.csv"},
    )


@app.get("/latest", response_model=ApiMeasurement)
async def get_latest():
    """
    Returns the latest measurement from the database
    """
    m = await Measurement.all().order_by("-time").limit(1)
    try:
        return ApiMeasurement.from_orm(m[0])
    except IndexError:
        return


def sync_get_latest():
    """
    Synchroneous db read of latest item for
    our plotly dashboard
    """
    with safe_conn() as c:
        df = pd.read_sql(
            'SELECT "usv","counter_id","time","id","acpm","cpm" FROM "measurement" ORDER BY "time" DESC LIMIT 1',
            c,
            parse_dates=["time"],
        )
        return df


def sync_moving_average():
    """
    Returns a Dataframe with a subsampling
    over all our data.
    """

    with safe_conn() as c:
        for idx, chunk in enumerate(
            pd.read_sql(
                'select * from measurement ORDER BY "time" ASC', c, chunksize=1000
            )
        ):
            if idx == 0:
                if len(chunk) < 100:
                    # one chunk, too small to subsample
                    df = chunk
                else:
                    df = chunk[::10]
            else:
                df = df.append(chunk[::10])

        try:
            return df
        except UnboundLocalError:
            # empty database
            return None


@app.get("/url-list", dependencies=[Depends(protect)])
def get_all_urls():
    url_list = [{"path": route.path, "name": route.name} for route in app.routes]
    return url_list


def get_last_24_hours():
    """
    Returns the last 24 hours worth of
    data packed in a pandas Dataframe
    """
    with safe_conn() as c:
        now_minus_24 = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        sql = Measurement.filter(time__gte=now_minus_24).order_by("time").sql()
        return pd.read_sql(sql, c, parse_dates=["time"])


@app.on_event("startup")
def startup_event():
    dash_app = build_app_from_data(
        get_last_24_hours, sync_get_latest, sync_moving_average
    )
    app.mount("/dashboard", WSGIMiddleware(dash_app.server))


@app.get("/")
async def home():
    return RedirectResponse("/dashboard")
