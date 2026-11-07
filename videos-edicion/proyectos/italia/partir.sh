#!/bin/bash
# Corta el documental en 6 partes (por capítulos), refuerza la marca del canal y comprime a ~7 Mbps.
cd "$(dirname "$0")/salida"
T=(0 217.5 457.5 619.5 803.5 953.5 99999)
for i in 0 1 2 3 4 5; do
  ini=${T[$i]}; dur=$(python3 -c "print(${T[$((i+1))]}-$ini)")
  en=""; [ $i = 0 ] && en=":enable='gte(t,10.5)'"
  ffmpeg -v error -y -ss $ini -t $dur -i Italia_documental.mp4 -i marca.png \
    -filter_complex "[0:v][1:v]overlay=0:0$en[v]" -map "[v]" -map 0:a \
    -c:v libx264 -preset medium -tune grain -b:v 7M -maxrate 9M -bufsize 14M -pix_fmt yuv420p -threads 2 \
    -c:a aac -b:a 192k -movflags +faststart partes/Italia_parte_$((i+1))_de_6.mp4 &
  if [ $i = 2 ]; then wait; fi
done
wait
