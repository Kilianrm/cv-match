import { CfnOutput, Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import { Construct } from 'constructs';

import { applyConventions, FoundationConfig } from '../../../bin/conventions';

export interface ComputeStackProps extends StackProps {
  foundation: FoundationConfig;
  vpc: ec2.IVpc;
}

export class ComputeStack extends Stack {
  public readonly cluster: ecs.ICluster;

  constructor(scope: Construct, id: string, props: ComputeStackProps) {
    super(scope, id, props);

    applyConventions(props.foundation, 'compute', this);

    const serviceConnectNamespace = `${props.foundation.appName}-${props.foundation.stage}.local`;

    this.cluster = new ecs.Cluster(this, 'SharedCluster', {
      vpc: props.vpc,
      clusterName: `${props.foundation.appName}-${props.foundation.stage}-shared-cluster`,
      defaultCloudMapNamespace: {
        name: serviceConnectNamespace,
        useForServiceConnect: true,
      },
    });

    new CfnOutput(this, 'SharedEcsClusterName', {
      value: this.cluster.clusterName,
      description: 'Shared ECS cluster used by application services in this environment.',
    });

    new CfnOutput(this, 'ServiceConnectNamespace', {
      value: serviceConnectNamespace,
      description: 'Cloud Map namespace used as the default ECS Service Connect namespace.',
    });
  }
}