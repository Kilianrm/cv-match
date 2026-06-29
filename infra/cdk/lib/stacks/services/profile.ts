import * as fs from 'node:fs';
import * as path from 'node:path';

import { CfnOutput, Duration, Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecsPatterns from 'aws-cdk-lib/aws-ecs-patterns';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
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

export interface ProfileServiceStackProps extends StackProps {
  foundation: FoundationConfig;
  vpc: ec2.IVpc;
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

    const imageDirectory = props.serviceImageDirectory ?? findRepoPath('services', 'profile-service');
    const servicePort = props.servicePort ?? 8080;

    const cluster = new ecs.Cluster(this, 'ProfileCluster', {
      vpc: props.vpc,
    });

    const environment: Record<string, string> = {
      SERVICE_NAME: 'profile-service',
      SERVICE_PORT: servicePort.toString(),
      LOG_LEVEL: props.logLevel ?? 'INFO',
      POSTGRES_HOST: props.databaseHost,
      POSTGRES_PORT: '5432',
      POSTGRES_DB: 'profile_db',
      AWS_REGION: props.foundation.env.region ?? this.region,
      CV_BUCKET_NAME: props.cvBucket.bucketName,
    };

    const service = new ecsPatterns.ApplicationLoadBalancedFargateService(this, 'ProfileService', {
      cluster,
      publicLoadBalancer: false,
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
        secrets: {
          POSTGRES_USER: ecs.Secret.fromSecretsManager(props.databaseSecret, 'username'),
          POSTGRES_PASSWORD: ecs.Secret.fromSecretsManager(props.databaseSecret, 'password'),
        },
        logDriver: ecs.LogDrivers.awsLogs({ streamPrefix: 'profile-service' }),
      },
    });

    props.cvBucket.grantReadWrite(service.taskDefinition.taskRole);

    service.targetGroup.configureHealthCheck({
      path: '/health',
      healthyHttpCodes: '200',
    });

    this.serviceUrl = `http://${service.loadBalancer.loadBalancerDnsName}`;

    new CfnOutput(this, 'ProfileServiceUrl', {
      value: this.serviceUrl,
      description: 'Internal URL for the profile-service ALB in this environment.',
    });
  }
}