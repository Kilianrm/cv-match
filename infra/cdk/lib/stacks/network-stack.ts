import { CfnOutput, Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';
import { applyConventions, FoundationConfig } from '../../bin/conventions';

export interface BoundaryStackProps extends StackProps {
  foundation: FoundationConfig;
}

export class NetworkStack extends Stack {
  public readonly vpc: ec2.IVpc;
  public readonly serviceSecurityGroup: ec2.ISecurityGroup;
  public readonly databaseSecurityGroup: ec2.ISecurityGroup;

  constructor(scope: Construct, id: string, props: BoundaryStackProps) {
    super(scope, id, props);

    applyConventions(props.foundation, 'network', this);

    this.vpc = new ec2.Vpc(this, 'Vpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          name: 'public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: 'private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        },
        {
          name: 'isolated',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
          cidrMask: 28,
        },
      ],
    });

    this.serviceSecurityGroup = new ec2.SecurityGroup(this, 'ServiceSecurityGroup', {
      vpc: this.vpc,
      description: 'Shared security group baseline for application services in private subnets.',
      allowAllOutbound: true,
    });

    this.serviceSecurityGroup.addIngressRule(
      this.serviceSecurityGroup,
      ec2.Port.allTcp(),
      'Allow east-west TCP traffic between application services.',
    );

    this.databaseSecurityGroup = new ec2.SecurityGroup(this, 'DatabaseSecurityGroup', {
      vpc: this.vpc,
      description: 'Database security group baseline for PostgreSQL access from application services.',
      allowAllOutbound: false,
    });

    this.databaseSecurityGroup.addIngressRule(
      this.serviceSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow PostgreSQL traffic from application services.',
    );

    new CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId,
      description: 'VPC used by CV Match application stacks.',
    });

    new CfnOutput(this, 'VpcCidr', {
      value: this.vpc.vpcCidrBlock,
      description: 'CIDR block allocated to the CV Match VPC.',
    });

    new CfnOutput(this, 'ServiceSecurityGroupId', {
      value: this.serviceSecurityGroup.securityGroupId,
      description: 'Shared application service security group.',
    });

    new CfnOutput(this, 'DatabaseSecurityGroupId', {
      value: this.databaseSecurityGroup.securityGroupId,
      description: 'Database security group for PostgreSQL access control.',
    });
  }
}
