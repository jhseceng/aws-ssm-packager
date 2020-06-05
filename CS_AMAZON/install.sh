#!/bin/bash
echo 'Starting'
REGION=`curl http://169.254.169.254/latest/dynamic/instance-identity/document|grep region|awk -F\" '{print $4}'`
echo $REGION
echo 'Configuring region'
aws configure set region $REGION

#aws Getting
echo 'Getting CID'
cid=`aws ssm get-parameter --name AgentActivationKey --query 'Parameter.Value' --output text`

echo $cid

sudo docker-compose down
yum install falcon-sensor-5.31.0-9606.amzn2.x86_64.rpm -y
/opt/CrowdStrike/falconctl -s --cid=$cid
service falcon-sensor start

sudo docker-compose up -d