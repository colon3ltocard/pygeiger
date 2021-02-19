export HOME_HOSTNAME=home.tocardise.eu
export DATABASE_URL=sqlite://db.sqlite3
uvicorn geigerserv:app --reload