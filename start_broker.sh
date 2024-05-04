#!/bin/bash

docker run -d --rm --name mqtt -p 1883:1883 eclipse-mosquitto:2.0.18 sh -c "echo -e 'listener 8081\\nprotocol websockets' >> mosquitto-no-auth.conf && mosquitto -c mosquitto-no-auth.conf"