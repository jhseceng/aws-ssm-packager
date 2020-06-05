#!/bin/bash
sudo apt-get install awscli -y
echo 'Starting'
REGION=`curl http://169.254.169.254/latest/dynamic/instance-identity/document|grep region|awk -F\" '{print $4}'`
echo $REGION
echo 'Configuring region'
aws configure set region $REGION

#aws Getting 
echo 'Getting CID'
cid=`aws ssm get-parameter --name AgentActivationKey --query 'Parameter.Value' --output text`

#installing from current directory 
sudo apt-get install libnl-3-200 libnl-genl-3-200 -y
sudo dpkg --install falcon-sensor_5.30.0-9510_amd64.deb
sudo /opt/CrowdStrike/falconctl -s --cid=$cid
sudo systemctl start falcon-sensor

# Add command to call installer.  For example "yum install .\ExamplePackage.rpm"