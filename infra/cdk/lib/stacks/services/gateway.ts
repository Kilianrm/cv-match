import * as fs from 'node:fs';
import * as path from 'node:path';

import { CfnOutput, Duration, Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecsPatterns from 'aws-cdk-lib/aws-ecs-patterns';
import { Construct } from 'constructs';

import { applyConventions, FoundationConfig } from '../../../bin/conventions';
import { EcsServiceLogging } from '../../constructs/ecs-logging';
import { createStandardServiceQueries, ServiceLogInsightsQueries } from '../../constructs/log-insights-queries';

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
  cluster: ecs.ICluster;
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

    const serviceLogging = new EcsServiceLogging(this, 'GatewayServiceLogging', {
      foundation: props.foundation,
      serviceName: 'gateway-service',
      streamPrefix: 'gateway-service',
    });

    new ServiceLogInsightsQueries(this, 'GatewayLogInsightsQueries', {
      appName: props.foundation.appName,
      stage: props.foundation.stage,
      serviceName: 'gateway-service',
      logGroupNames: [serviceLogging.logGroup.logGroupName],
      queries: createStandardServiceQueries('gateway-service'),
    });

    const environment: Record<string, string> = {
      SERVICE_NAME: 'gateway-service',
      ENVIRONMENT: props.foundation.stage,
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
      cluster: props.cluster,
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
        logDriver: serviceLogging.logDriver,
      },
    });

    // This ECS pattern doesn't expose serviceConnectConfiguration in constructor props.
    // Enable Service Connect directly on the underlying Fargate service instance.
    service.service.enableServiceConnect();

    service.targetGroup.configureHealthCheck({
      path: '/health',
      healthyHttpCodes: '200',
    });

    new CfnOutput(this, 'GatewayServiceUrl', {
      value: `http://${service.loadBalancer.loadBalancerDnsName}`,
      description: 'Public URL for the gateway-service ALB in this environment.',
    });

    new CfnOutput(this, 'GatewayServiceLogGroupName', {
      value: serviceLogging.logGroup.logGroupName,
      description: 'CloudWatch Logs group for gateway-service ECS task logs.',
    });
  }
}