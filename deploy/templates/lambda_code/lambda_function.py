import boto3


class AWSBotoAdapter:

    def __init__(self, region):
        self.aws_region = region

    def get_resource(self, resource):
        aws_connection = boto3.session.Session(region_name=self.aws_region)
        resource = aws_connection.resource(resource, region_name = self.aws_region)
        return resource

    def get_client(self, client):
        aws_connection = boto3.session.Session(region_name=self.aws_region)
        client = aws_connection.client(client, region_name = self.aws_region)
        return client


class Ec2Adapter:

    def __init__(self, region):
        self.__resource = 'ec2'
        self.__region = region
        self.__connection = AWSBotoAdapter(region)

    def __get_connection_ec2(self):
        return self.__connection.get_client(self.__resource)

    def describe_instance(self, instanceId):
        return self.__get_connection_ec2().describe_instances(InstanceIds=[instanceId])


class AsgAdapter:
    def __init__(self, region):
        self.__region = region
        self.__resource = 'autoscaling'
        self.__connection = AWSBotoAdapter(region)
        self.desired_capacity_ondemand = 3

    def __get_connection_asg(self):
        return self.__connection.get_client(self.__resource)

    def describe_autoscaling_ondemand(self, service_name):
        paginator = self.__get_connection_asg().get_paginator('describe_auto_scaling_groups')
        page_iterator = paginator.paginate(
            PaginationConfig={'PageSize': 100}
        )
        filtered_asgs = page_iterator.search('AutoScalingGroups[] | [?contains(Tags[?Key==`{}`].Value, `{}`)]'.format(
            'service', service_name))
        for asg in filtered_asgs:
            for tag in asg['Tags']:
                if tag['Key'] == "lifecycle" and tag['Value'] == 'ondemand':
                    autoscaling_name = asg['AutoScalingGroupName']
        return autoscaling_name

    def autoscale_ondemand_autoscaling(self, autoscaling_ondemand):
        print("scaling " + autoscaling_ondemand)
        result = self.__get_connection_asg().set_desired_capacity(
            AutoScalingGroupName=autoscaling_ondemand,
            DesiredCapacity=self.desired_capacity_ondemand
        )
        return result


def lambda_handler(event, context):
    print(event)
    instanceId = event['detail']['instance-id']
    region = 'eu-west-1'
    ec2Connection = Ec2Adapter(region)
    asgConnection = AsgAdapter(region)
    instanceTags = ec2Connection.describe_instance(instanceId)['Reservations'][0]['Instances'][0]['Tags']
    for tag in instanceTags:
        if tag['Key'] == 'service':
            service_name = tag['Value']
    autoscaling_ondemand = asgConnection.describe_autoscaling_ondemand(service_name)
    print(asgConnection.autoscale_ondemand_autoscaling(autoscaling_ondemand))
    return "Instance " + instanceId + " Spot termination request, ondemand autoscaling action performed"
    #raise Exception('Something went wrong')
