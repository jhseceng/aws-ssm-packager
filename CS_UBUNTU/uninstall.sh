#!/bin/bash

echo 'Uninstalling Crowdstrike on Amazon Linux...'
echo 'Starting'
REGION=`curl http://169.254.169.254/latest/dynamic/instance-identity/document|grep region|awk -F\" '{print $4}'`
echo $REGION
echo 'Configuring region'
aws configure set region $REGION

# Get API Keys from Parameter Store
echo 'Getting API keys'
APIKEY=$(aws ssm get-parameter --name APIKey --query 'Parameter.Value' --output text)
APISECRET=$(aws ssm get-parameter --name APISecret --query 'Parameter.Value' --output text)

#Get AID and remove local files to cleanup
echo 'Getting the AID for the instance'
aid=$(sudo /opt/CrowdStrike/falconctl -g --aid | awk -F\" '{print $2}')
echo $aid
sudo apt-get purge falcon-sensor

#With AID and API keys, delete host on Crowdstrike console
#Get OAuth2 Token
echo 'Getting OAuth2 Token'
TOKEN=$(curl -X POST "https://api.crowdstrike.com/oauth2/token" -H "accept: application/json" -H "Content-Type: application/x-www-form-urlencoded" -d "client_id"=""$APIKEY"&client_secret"="$APISECRET" | grep access_token| awk -F\" '{print $4}')
echo $TOKEN

# Check to see if AID is present
echo 'Getting the AID and verifying against Falcon console'
aid_status=$(curl -X GET "https://api.crowdstrike.com/devices/entities/devices/v1?ids"="$aid" -H "Accept: application/json" -H "Authorization: Bearer "$TOKEN"")
echo $aid_status

# Will need to add some sort of HTTP status check here 

# Delete with AID
echo "Now deleting the host on Falcon Console"
aid_delete=$(curl -X POST "https://api.crowdstrike.com/devices/entities/devices-actions/v2?action_name=hide_host" -H "accept: application/json" -H "authorization: bearer ""$TOKEN" -H "Content-Type: application/json" -d "{ \"action_parameters\": [ { \"name\": \"string\", \"value\": \"string\" } ], \"ids\": [ \"$aid\" ]}")
echo $aid_delete

# Will need to add some sort of HTTP status check here 