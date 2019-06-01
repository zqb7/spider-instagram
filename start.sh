#!/bin/bash

filename="instagram.py"
for line in `tail -n +2 author.list`
do
echo $line|awk -F "|" '{print "exec python instagram.py --name "$1 " --proxy "$2 " --sleep 5"}'|sh
done