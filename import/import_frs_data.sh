#!/bin/bash 

FRS_DIR=$1

cat $FRS_DIR/FRS_FACILITIES.csv | psql -c '\COPY frs.facilities FROM STDIN WITH CSV HEADER;'
cat $FRS_DIR/FRS_PROGRAM_LINKS.csv | psql -c '\COPY frs.program_links FROM STDIN WITH CSV HEADER;'

