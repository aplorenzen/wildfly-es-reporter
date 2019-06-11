#!/bin/bash

while true; do
    sleep 5
    echo "Starting push..."
    ./push_wildfly_bean_stats_to_elastic.sh
done
