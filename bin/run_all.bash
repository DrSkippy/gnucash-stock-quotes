set -e

echo "************************STARTING************************"
echo "Running daily fetch script..."
./bin/daily_fetch.py
echo "Tickers fetched successfully..."
./bin/shak.py -l
echo "Running GnuCash script..."
./bin/shak.py gnucash
echo "Running correlation script for IONQ and QBTS..."
./bin/shak.py compare -c IONQ QBTS
echo "Running indexes script..."
./bin/shak.py index
echo "************************COMPLETED************************"
