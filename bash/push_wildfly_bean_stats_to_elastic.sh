#!/bin/bash

curl -s --digest --user etel:etel 'http://localhost:9990/management/deployment/etel.ear/subdeployment/etel-ejb-1.0-SNAPSHOT.jar/subsystem/ejb3/stateless-session-bean/' | jq -r '."stateless-session-bean" | keys[]' | xargs -l -I {} sh -c "./post_to_elasticsearch.sh {}"


