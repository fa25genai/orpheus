#!/bin/bash
#

echo "Exporting Orpheus logs from docker-compose..."

mkdir -p logs
docker-compose logs &> logs/full.txt
grep -v DEBUG logs/full.txt > logs/info.txt
grep -e "^ui" logs/full.txt > logs/ui.txt
grep -e "^core" logs/full.txt > logs/core.txt
grep -e "^slides" logs/full.txt > logs/slides.txt
grep -e "^avatar" logs/full.txt > logs/avatar.txt
grep -e "^docint" logs/full.txt > logs/docint.txt
grep -e "^status" logs/full.txt > logs/status.txt

