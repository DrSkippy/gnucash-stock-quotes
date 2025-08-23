cd /home/scott/Working/gnucash-stock-quotes
export PYTHONPATH=$(pwd)
/home/scott/.local/bin/poetry run python ./bin/daily_fetch.py
cd -
