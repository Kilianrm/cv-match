import { CfnOutput, Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';
import { applyConventions, FoundationConfig } from '../../../bin/conventions';

export interface SecurityStackProps extends StackProps {
  foundation: FoundationConfig;
  vpc: ec2.IVpc;
  allowDatabasePublicAccess?: boolean;
  databasePublicAccessCidr?: string;
}

export class SecurityStack extends Stack {
  public readonly serviceSecurityGroup: ec2.ISecurityGroup;
  public readonly databaseSecurityGroup: ec2.ISecurityGroup;

  constructor(scope: Construct, id: string, props: SecurityStackProps) {
    super(scope, id, props);

    applyConventions(props.foundation, 'security', this);

    this.serviceSecurityGroup = new ec2.SecurityGroup(this, 'ServiceSecurityGroup', {
      vpc: props.vpc,
      description: 'Shared security group baseline for application services in private subnets.',
      allowAllOutbound: true,
    });

    this.serviceSecurityGroup.addIngressRule(
      this.serviceSecurityGroup,
      ec2.Port.allTcp(),
      'Allow east-west TCP traffic between application services.',
    );

    this.databaseSecurityGroup = new ec2.SecurityGroup(this, 'DatabaseSecurityGroup', {
      vpc: props.vpc,
      description: 'Database security group baseline for PostgreSQL access from application services.',
      allowAllOutbound: false,
    });

    this.databaseSecurityGroup.addIngressRule(
      this.serviceSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow PostgreSQL traffic from application services.',
    );

    if (props.allowDatabasePublicAccess) {
      if (!props.databasePublicAccessCidr) {
        throw new Error(
          'SecurityStack requires databasePublicAccessCidr when allowDatabasePublicAccess is enabled.',
        );
      }

      this.databaseSecurityGroup.addIngressRule(
        ec2.Peer.ipv4(props.databasePublicAccessCidr),
        ec2.Port.tcp(5432),
        'Allow PostgreSQL traffic from configured public CIDR range.',
      );
    }

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