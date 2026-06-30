import * as fs from 'node:fs';
import * as path from 'node:path';

import { CfnOutput, Duration, Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecsPatterns from 'aws-cdk-lib/aws-ecs-patterns';
import { Construct } from 'constructs';

import { applyConventions, FoundationConfig } from '../../../bin/conventions';

function findRepoPath(...targetSegments: string[]): string {
  let currentDirectory = __dirname;

  while (true) {
    const candidatePath = path.join(currentDirectory, ...targetSegments);
    if (fs.existsSync(candidatePath)) {
      return candidatePath;
    }

    const parentDirectory = path.dirname(currentDirectory);
    if (parentDirectory === currentDirectory) {
      throw new Error(`Could not resolve path for ${targetSegments.join('/')}`);
    }

    currentDirectory = parentDirectory;
  }
}

export interface GatewayServiceStackProps extends StackProps {
  foundation: FoundationConfig;
  vpc: ec2.IVpc;
  securityGroups?: ec2.ISecurityGroup[]; // ?: Optional security groups for the ECS service. If not provided, the default security group of the VPC will be used.
  profileServiceBaseUrl: string;
  serviceImageDirectory?: string;
  desiredCount?: number;
  cpu?: number;
  memoryLimitMiB?: number;
  servicePort?: number;
  localAuthBypass?: boolean;
  cognitoClientId?: string;
  jwksUrl?: string;
}

export class GatewayServiceStack extends Stack {
  constructor(scope: Construct, id: string, props: GatewayServiceStackProps) {
    super(scope, id, props);

    applyConventions(props.foundation, 'gateway', this);

    const imageDirectory = props.serviceImageDirectory ?? findRepoPath('services', 'gateway');
    const servicePort = props.servicePort ?? 8000;

    const cluster = new ecs.Cluster(this, 'GatewayCluster', {
      vpc: props.vpc,
    });

    const environment: Record<string, string> = {
      SERVICE_NAME: 'gateway-service',
      SERVICE_PORT: servicePort.toString(),
      PROFILE_SERVICE_URL: props.profileServiceBaseUrl,
      LOCAL_AUTH_BYPASS: String(props.localAuthBypass ?? false),
    };

    if (props.cognitoClientId) {
      environment.COGNITO_CLIENT_ID = props.cognitoClientId;
    }

    if (props.jwksUrl) {
      environment.JWKS_URL = props.jwksUrl;
    }

    // High-level ECS pattern that wires the full public entrypoint:
    // - ALB: internet-facing entrypoint in public subnets
    // - listener: accepts incoming HTTP traffic on the load balancer
    // - target group: routes traffic from the ALB to the ECS tasks
    // - Fargate service: runs the gateway container in private subnets
    // - task definition/container: injects these environment values at runtime
    const service = new ecsPatterns.ApplicationLoadBalancedFargateService(this, 'GatewayService', {
      cluster,
      publicLoadBalancer: true,
      desiredCount: props.desiredCount ?? 1,
      cpu: props.cpu ?? 512,
      memoryLimitMiB: props.memoryLimitMiB ?? 1024,
      circuitBreaker: {
        rollback: true,
      },
      minHealthyPercent: 100,
      maxHealthyPercent: 200,
      ...(props.securityGroups && { securityGroups: props.securityGroups }),
      assignPublicIp: false,
      taskSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      healthCheckGracePeriod: Duration.seconds(60),
      taskImageOptions: {
        image: ecs.ContainerImage.fromAsset(imageDirectory, {
          file: 'docker/Dockerfile',
        }),
        containerPort: servicePort,
        environment,
        logDriver: ecs.LogDrivers.awsLogs({ streamPrefix: 'gateway-service' }),
      },
    });

    service.targetGroup.configureHealthCheck({
      path: '/health',
      healthyHttpCodes: '200',
    });

    new CfnOutput(this, 'GatewayServiceUrl', {
      value: `http://${service.loadBalancer.loadBalancerDnsName}`,
      description: 'Public URL for the gateway-service ALB in this environment.',
    });
  }
}