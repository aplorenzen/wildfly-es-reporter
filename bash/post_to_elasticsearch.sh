#!/bin/bash

curl -s --digest --user etel:etel
'http://localhost:9990/management/deployment/etel.ear/subdeployment/etel-ejb-1.0-SNAPSHOT.jar/subsystem/ejb3/stateless-session-bean/'$1'/read-resource?include-runtime=true&recursive=true' |
jq --arg time $(date -u +'%Y-%m-%dT%T.%3N') '. + {date: $time}' |
curl -s -X POST 'http://localhost:9200/etel/stats' -H 'Content-Type: application/json' -d @- | jq
