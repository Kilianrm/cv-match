import * as fs from 'node:fs';
import * as path from 'node:path';

import { CfnOutput, Duration, Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
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

export interface ProfileServiceStackProps extends StackProps {
  foundation: FoundationConfig;
  vpc: ec2.IVpc;
  cluster: ecs.ICluster;
  databaseSecret: secretsmanager.ISecret;
  databaseHost: string;
  cvBucket: s3.IBucket;
  securityGroups?: ec2.ISecurityGroup[];
  serviceImageDirectory?: string;
  desiredCount?: number;
  cpu?: number;
  memoryLimitMiB?: number;
  servicePort?: number;
  logLevel?: string;
}

export class ProfileServiceStack extends Stack {
  public readonly serviceUrl: string;

  constructor(scope: Construct, id: string, props: ProfileServiceStackProps) {
    super(scope, id, props);

    applyConventions(props.foundation, 'profile', this);

    const imageDirectory = props.serviceImageDirectory ?? findRepoPath('services', 'profile');
    const servicePort = props.servicePort ?? 8080;

    const serviceLogging = new EcsServiceLogging(this, 'ProfileServiceLogging', {
      foundation: props.foundation,
      serviceName: 'profile-service',
      streamPrefix: 'profile-service',
    });

    // Keep the historical logical ID to avoid replacing a named log group
    // after moving log-group creation behind a reusable construct.
    const profileLogGroupCfn = serviceLogging.logGroup.node.defaultChild as logs.CfnLogGroup;
    profileLogGroupCfn.overrideLogicalId('ProfileServiceLogGroup');

    new ServiceLogInsightsQueries(this, 'ProfileLogInsightsQueries', {
      appName: props.foundation.appName,
      stage: props.foundation.stage,
      serviceName: 'profile-service',
      logGroupNames: [serviceLogging.logGroup.logGroupName],
      queries: createStandardServiceQueries('profile-service'),
    });

    const environment: Record<string, string> = {
      SERVICE_NAME: 'profile-service',
      ENVIRONMENT: props.foundation.stage,
      SERVICE_PORT: servicePort.toString(),
      LOG_LEVEL: props.logLevel ?? 'INFO',
      POSTGRES_HOST: props.databaseHost,
      POSTGRES_PORT: '5432',
      POSTGRES_DB: 'profile_db',
      AWS_REGION: props.foundation.env.region ?? this.region,
      CV_BUCKET_NAME: props.cvBucket.bucketName,
    };

    const taskDefinition = new ecs.FargateTaskDefinition(this, 'ProfileServiceTaskDef', {
      cpu: props.cpu ?? 512,
      memoryLimitMiB: props.memoryLimitMiB ?? 1024,
    });

    taskDefinition.addContainer('ProfileServiceContainer', {
      image: ecs.ContainerImage.fromAsset(imageDirectory, {
        file: 'docker/Dockerfile',
      }),
      logging: serviceLogging.logDriver,
      environment,
      secrets: {
        POSTGRES_USER: ecs.Secret.fromSecretsManager(props.databaseSecret, 'username'),
        POSTGRES_PASSWORD: ecs.Secret.fromSecretsManager(props.databaseSecret, 'password'),
      },
      portMappings: [
        {
          containerPort: servicePort,
          name: 'profile-http',
          protocol: ecs.Protocol.TCP,
          appProtocol: ecs.AppProtocol.http,
        },
      ],
    });

    const service = new ecs.FargateService(this, 'ProfileService', {
      cluster: props.cluster,
      taskDefinition,
      desiredCount: props.desiredCount ?? 1,
      circuitBreaker: {
        rollback: true,
      },
      minHealthyPercent: 100,
      maxHealthyPercent: 200,
      securityGroups: props.securityGroups,
      assignPublicIp: false,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      healthCheckGracePeriod: Duration.seconds(60),
      serviceConnectConfiguration: {
        services: [
          {
            portMappingName: 'profile-http',
            discoveryName: 'profile-service',
            dnsName: 'profile-service',
            port: servicePort,
          },
        ],
      },
    });

    // Gateway no longer needs to share the same SG; allow VPC-internal callers
    // to reach the profile service port for Service Connect traffic.
    for (const securityGroup of service.connections.securityGroups) {
      securityGroup.addIngressRule(
        ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
        ec2.Port.tcp(servicePort),
        'Allow VPC-internal traffic to profile-service port.',
      );
    }

    props.cvBucket.grantReadWrite(taskDefinition.taskRole);

    this.serviceUrl = `http://profile-service:${servicePort}`;

    new CfnOutput(this, 'ProfileServiceUrl', {
      value: this.serviceUrl,
      description: 'Internal Service Connect URL for profile-service in this environment.',
    });

    new CfnOutput(this, 'ProfileServiceLogGroupName', {
      value: serviceLogging.logGroup.logGroupName,
      description: 'CloudWatch Logs group for profile-service ECS task logs.',
    });
  }
}