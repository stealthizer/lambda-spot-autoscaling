#!/usb/bin/env python3

from troposphere import Parameter, Ref, Template, Join, GetAtt
from troposphere.awslambda import Function, Code, Permission
from troposphere.events import Rule, Target
from troposphere.iam import Role, Policy
from troposphere.dynamodb import (KeySchema, AttributeDefinition,
                                  ProvisionedThroughput, TimeToLiveSpecification)
from troposphere.dynamodb import Table


class MultiAutomatedRecoveryControl(object):
    def __init__(self, sceptre_user_data):
        self.sceptre_user_data = sceptre_user_data
        self.add_template()
        self.add_dynamobd_terminate_db()
        self.add_lambda_execution_role()
        self.add_lambda_function()
        self.add_target_lambda()
        self.add_event_rule()
        self.add_target_lambda_demo()
        self.add_event_rule_demo()
        self.add_lambda_permission_ec2()
        self.add_lambda_permission_demo()



    def add_template(self):
        self.template = Template()
        self.template.add_description(
            "multi Automated Recovery Control Lambda"
        )

    def add_dynamobd_terminate_db(self):
        self.terminate_dynamodb = self.template.add_resource(
            Table(
            "terminationDB",
            TableName="terminateDB",
            TimeToLiveSpecification=TimeToLiveSpecification(AttributeName="ttl", Enabled=True),
            AttributeDefinitions=[
                AttributeDefinition(
                    AttributeName="termination",
                    AttributeType="S"
                ),
            ],
            KeySchema=[
                KeySchema(
                    AttributeName="termination",
                    KeyType="HASH"
                )
            ],
            ProvisionedThroughput=ProvisionedThroughput(
                ReadCapacityUnits=2,
                WriteCapacityUnits=1
            )
        ))
    def add_lambda_execution_role(self):
        self.lambdaExecutionRole = self.template.add_resource(Role(
            "LambdaExecutionRolemARC",
            Path="/",
            Policies=[
                Policy(
                    PolicyName="root",
                    PolicyDocument={
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                            "Action": "logs:*",
                            "Resource": "arn:aws:logs:*:*:*",
                            "Effect": "Allow"
                            }
                        ]
                    }
                ),
                Policy(
                    PolicyName="Ec2",
                    PolicyDocument={
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Sid": "Ec2Describeinstances",
                                "Effect": "Allow",
                                "Action": [
                                    "ec2:DescribeInstances",
                                    "ec2:DescribeInstanceStatus"
                                ],
                                "Resource": "*"
                            }
                        ]
                    }
                ),
                Policy(
                    PolicyName="Autoscaling",
                    PolicyDocument={
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Sid": "AutoscalingSetDesiredCapacity",
                                "Effect": "Allow",
                                "Action": "autoscaling:SetDesiredCapacity",
                                "Resource": "arn:aws:autoscaling:*:*:autoScalingGroup:*:autoScalingGroupName/*"
                            },
                            {
                                "Sid": "AutoscalingDescribeGroups",
                                "Effect": "Allow",
                                "Action": "autoscaling:DescribeAutoScalingGroups",
                                "Resource": "*"
                            }
                        ]
                    }
                ),
                Policy(
                    PolicyName="Events",
                    PolicyDocument={
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Sid": "CloudWatchEventsFullAccess",
                                "Effect": "Allow",
                                "Action": "events:*",
                                "Resource": "*"
                            },
                            {
                                "Sid": "IAMPassRoleForCloudWatchEvents",
                                "Effect": "Allow",
                                "Action": [
                                    "iam:PassRole",
                                    "lambda:InvokeFunction"
                                    ],
                                "Resource": "arn:aws:iam::*:role/AWS_Events_Invoke_Targets"
                            }
                    ]
                    }
                )
            ],
            AssumeRolePolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": ["sts:AssumeRole"],
                        "Effect": "Allow",
                        "Principal": {
                        "Service": [
                            "lambda.amazonaws.com",
                            "events.amazonaws.com"
                        ]
                     }
                     }
                ]
            },
        ))

    def add_lambda_function(self):
        lambda_code = open("templates/lambda_code/lambda_function.py", "r")
        self.lambda_function = self.template.add_resource(Function(
            "SpotTerminatingSceptre",
            FunctionName="Spot_Terminate_Sceptre",
            Description="Function that trigers when a spot instance is marked for termination due to outbid",
            Code=Code(
                ZipFile=lambda_code.read()
            ),
            Handler="index.lambda_handler",
            Role=GetAtt("LambdaExecutionRolemARC", "Arn"),
            Runtime="python3.6",
        ))

    def add_target_lambda(self):
        self.lambda_target = Target(
            "SpotLambdaTarget",
            Arn=GetAtt(self.lambda_function, 'Arn'),
            Id="LambdaTarget"
        )

    def add_event_rule(self):
        self.rule = self.template.add_resource(Rule(
            "SpotRule",
            Description="Rule trigered when a spot termination notice is found",
            EventPattern={
                "source": [
                    "aws.ec2"
                ],
                "detail-type": [
                    "EC2 Spot Instance Interruption Warning"
                ],
                "detail": {
                    "instance-action": ["terminate"]
                }
            },
            State="ENABLED",
            Targets=[self.lambda_target]
        ))

    def add_target_lambda_demo(self):
        self.lambda_target = Target(
            "SpotLambdaTargetDemo",
            Arn=GetAtt(self.lambda_function, 'Arn'),
            Id="LambdaTarget2"
        )

    def add_event_rule_demo(self):
        self.rule_demo = self.template.add_resource(Rule(
            "SpotRuleDemo",
            Description="Rule trigered when a spot termination notice is found",
            EventPattern={
                "source": [
                    "mARC_demo"
                ],
                "detail-type": [
                    "EC2 Spot Instance Interruption Warning"
                ],
                "detail": {
                    "instance-action": ["terminate"]
                }

            },
            State="ENABLED",
            Targets=[self.lambda_target]
        ))

    def add_lambda_permission_ec2(self):
        self.lambda_permission_ec2 = self.template.add_resource(Permission(
            "LambdaEc2Permission",
            Action='lambda:InvokeFunction',
            FunctionName=GetAtt(self.lambda_function, 'Arn'),
            Principal="events.amazonaws.com",
            SourceArn=GetAtt(self.rule, 'Arn'),
        ))

    def add_lambda_permission_demo(self):
        self.lambda_permission_demo = self.template.add_resource(Permission(
            "LambdaDemoPermission",
            Action='lambda:InvokeFunction',
            FunctionName=GetAtt(self.lambda_function, 'Arn'),
            Principal="events.amazonaws.com",
            SourceArn=GetAtt(self.rule_demo, 'Arn'),
        ))


def sceptre_handler(sceptre_user_data):
    sceptre = MultiAutomatedRecoveryControl(sceptre_user_data)
    return sceptre.template.to_json()
