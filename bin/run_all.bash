set -e
echo "Running daily fetch script..."
./bin/daily_fetch.py
echo "Running GnuCash script..."
./bin/gnucash.py
echo "Running correlation script for IONQ and QBTS..."
./bin/correlation.py -s IONQ QBTS
echo "Running indexes script..."
./bin/indexes.py
echo "************************COMPLETED************************"
