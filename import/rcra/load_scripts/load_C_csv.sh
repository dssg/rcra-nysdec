#!/bin/bash -xv

RCRA_DIR=$1
echo loading cmecomp3 into the database ...
$RCRA_DIR/C/cmecomp3.csv | psql -c '\COPY rcra.cmecomp3 FROM STDIN WITH CSV HEADER'
echo rcra.cmecomp3 has been loaded into the database.

echo loading ccitation into the database ...
$RCRA_DIR/C/ccitation.csv | psql -c '\COPY rcra.ccitation FROM STDIN WITH CSV HEADER'
echo rcra.ccitation has been loaded into the database.

echo loading lu_citation into the database ...
$RCRA_DIR/C/lu_citation.csv | psql -c '\COPY rcra.lu_citation FROM STDIN WITH CSV HEADER'
echo rcra.lu_citation has been loaded into the database.
