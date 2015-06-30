#!/bin/sh 
DB=/srv/webapps/frackbox/data/db.sqlite3 
/srv/webapps/frackbox/utilities/genFBnSPtables.py $DB 
/srv/webapps/frackbox/utilities/grabbweather.py $DB 
echo "Duplicated database: 'cp ../data/db.sqlite3 /srv/shiny-server/db.sqlite3'"
