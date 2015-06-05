#!/bin/sh 
DB=/srv/webapps/frackbox/data/db.sqlite3 
/srv/webapps/frackbox/utilities/genFBnSPtables.py $DB 
/srv/webapps/frackbox/utilities/grabbweather.py $DB 
