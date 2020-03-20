#!/usr/bin/env zsh

rm -rf ddnet-sql ddnet-sql.zip
wget https://ddnet.tw/stats/ddnet-sql.zip
unzip ddnet-sql.zip

echo 'TRUNCATE record_race RESTART IDENTITY;' > record_race.psql
grep '^INSERT INTO' ddnet-sql/record_race.sql >> record_race.psql

perl -i -p -E "s/\\\'(?:(?!,\'))/\'\'/g" record_race.psql
sed -i 's/\\"/"/g' record_race.psql
sed -i 's/\\\\/\\/g' record_race.psql
sed -i "s/'0000-00-00 00:00:00'/NULL/g" record_race.psql
sed -i "s/\`record_race\`/record_race/g" record_race.psql

psql < record_race.psql

psql -c 'BEGIN; TRUNCATE stats_hours, stats_times RESTART IDENTITY; INSERT INTO stats_hours (name, hour, finishes) SELECT name, EXTRACT(HOUR FROM timestamp) AS hour, COUNT(*) FROM record_race GROUP BY name, hour; INSERT INTO stats_times (name, time) SELECT name, SUM(time) FROM record_race GROUP BY name; COMMIT;'
