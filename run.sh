export HOME_HOSTNAME=home.tocardise.eu
# export DATABASE_URL=sqlite://db.sqlite3
export DATABASE_URL=postgres://postgres:postgres@localhost:5432
uvicorn geigerserv:app --reload --host 0.0.0.0
