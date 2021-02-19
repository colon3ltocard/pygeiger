# GMC-320 geiger counter data acquisition webservice

This project is a website compatible with gq GMC-320+v5 wifi geiger counter. It stores the measurement pushed by the counter in a postgres db, forwards each measurement to the http://gmcmap.com website and exposes a dashboard.

The gmc-320 is a wifi enabled geiger counter which can produce measurements every minute. The following data are produced:

* CPM : Counts per minute of the geiger counter
* ACPM: Averaged CPM
* usV: value in uSv/h (beware that the device is not energy compensated)

See the [documentation from gq](http://www.gqelectronicsllc.com/GMC-320PlusV5UserGuide.pdf) and [Wikipedia](https://en.wikipedia.org/wiki/Geiger_counter)

## Configuring the device

For you GMC-320 device to work with an instance of this webservice you will need to modify the  **Website** and **URL** as described in the [documentation - Read it !](http://www.gqelectronicsllc.com/GMC-320PlusV5UserGuide.pdf).

In my case i have set:
```
Website: geiger.tocardise.eu
URL: upload
```
This will make the device produce HTTP GET requests like this *http://geiger.tocardise.eu/upload?AID=0230111&GID=0034021&CPM=15&ACPM=13.2&uSV=0.075*

Please note that trying to make this request yourself should be forbidden by the IP filtering. If you find a vulnerability please tell me :-)

## Overview 

My instance of this website is running at http://geiger.tocardise.eu, you can get the latest measurement here http://geiger.tocardise.eu/latest and the API doc here: http://geiger.tocardise.eu/docs

Sometimes I take my device for a trip so there is no data for a while.

It provides the following features:

* an HTTP endpoint for the GMC-320 to push data. data are optionaly forwarded to http://www.gmcmap.com
* a quick and dirty dask dashboard to see the last 24 hours of data
* an HTTP endpoint to download all data received so far
* an HTTP endpoint to retrieve the latest measurement (for real time monitoring)

It is also a technical playground to demonstrate several concepts:

* a simple webservice implemented using [fastapi](https://fastapi.tiangolo.com/) and [tortoise-orm](https://tortoise-orm.readthedocs.io)
* the integration in the fastapi app of a [dash dashboard](https://pypi.org/project/dash/)
* Streaming data out of a sql db using [pandas and chunking](https://pandas.pydata.org/docs/).
* the deployment of the webservice using [Heroku free dynos](https://www.heroku.com).
## Credits

Thanks to RealPython for their [dash tutorial](https://realpython.com/python-dash/).

## Run locally

It is possible to run the webservice locally using the `run.sh` script. A python virtualenv 
must be used with the requirements install like this (assuming pyenv is used):

Install pyenv using [pyenv-installer](https://github.com/pyenv/pyenv-installer) first.

```
pyenv install 3.8.8
pyenv virtualenv 3.8.8 geigerenv
pyenv activate geigerenv
pip install -r requirements.txt
```

Now you can run the app.

```
./run.sh
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [18688] using statreload
INFO:     Started server process [18728]
INFO:     Waiting for application startup.
```

You can upload fake data to your local instance using this request:

```
curl "http://127.0.0.1:8000/upload?AID=0230111&GID=0034021&CPM=15&ACPM=13.2&uSV=0.075"
OK.ERR0
```

## Deploying to Heroku

This repository has a `Procfile` and a `runtime.txt` file and is compatible with Heroku deployment.

Assuming you have created an Heroku account follow the steps below (replace geigerdemo by an app name of your choice):

```
curl https://cli-assets.heroku.com/install.sh | sh
heroku login
...
Logging in... done
Logged in as xx.xx@yyy.com
git clone https://github.com/colon3ltocard/pygeiger
cd pygeiger
heroku create geigerdemo
Creating ⬢ geigerdemo... done
https://geigerdemo.herokuapp.com/ | https://git.heroku.com/geigerdemo.git
git remote -v
heroku  https://git.heroku.com/geigerdemo.git (fetch)
```

We now add a database to our app (using hobby-dev free plan)
```
heroku addons:create heroku-postgresql:hobby-dev
Creating heroku-postgresql:hobby-dev on ⬢ geigerdemo... free
Database has been created and is available
 ! This database is empty. If upgrading, you can transfer
 ! data from another database with pg:copy
Created postgresql-transparent-62251 as DATABASE_URL
Use heroku addons:docs heroku-postgresql to view documentation
```

We need to configure two env variables expected by the webservice. The first one is **HOME_HOSTNAME** and is used to identify the hostname from which data
can be pushed (I find my home IP using a dyndns hostname). 

```
heroku config:set HOME_HOSTNAME=YOUR_DYNDNS_HOSTNAME
```

The second variable is optional and used to activate data forwarding
to http://gmcmap.com

```
heroku config:set FORWARD_TO_GMC=1
```

Finally we deploy the app.
```
git push heroku
Counting objects: 76, done.
Delta compression using up to 8 threads.
Compressing objects: 100% (72/72), done.
Writing objects: 100% (76/76), 11.24 KiB | 1.02 MiB/s, done.
Total 76 (delta 40), reused 0 (delta 0)
remote: Compressing source files... done.
remote: Building source:
remote:
remote: -----> Building on the Heroku-20 stack
remote: -----> Python app detected
remote: -----> Installing python-3.8.8
remote: -----> Installing pip 20.1.1, setuptools 47.1.1 and wheel 0.34.2
....
....
remote: -----> Launching...
remote:        Released v5
remote:        https://geigerdemo.herokuapp.com/ deployed to Heroku
```

You can now browse to your app at https://geigerdemo.herokuapp.com/. (Replace *geigerdemo* by your app name)

You can check the app logs at anytime using:

```
heroku logs --tail
```

**IMPORTANT SAVE YOUR FREE DYNO TIME** don't forget to stop your app by scaling the web workers to 0.

```
heroku ps:scale web=0
```

Finally, you can destroy the app like this:
```
heroku apps:destroy
 ▸    WARNING: This will delete ⬢ geigerdemo including all add-ons.
 ▸    To proceed, type geigerdemo or re-run this command with --confirm geigerdemo
 > geigerdemo
Destroying ⬢ geigerdemo (including all add-ons)... done
 ```

## LICENSE: The MIT License (MIT)

Copyright © 2021 Frank Guibert

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.