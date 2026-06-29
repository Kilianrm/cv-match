import { CfnOutput, RemovalPolicy, Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { applyConventions, FoundationConfig } from '../../../bin/conventions';

export interface SharedInfraStackProps extends StackProps {
  foundation: FoundationConfig;
  vpc: ec2.IVpc;
  databaseSecurityGroup?: ec2.ISecurityGroup;
  allowSelfManagedSecurityGroup?: boolean;
  publicDatabaseAccess?: boolean;
  publicDatabaseAccessCidr?: string;
}

export class DataStack extends Stack {
  public readonly database: rds.DatabaseInstance;
  public readonly cvBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: SharedInfraStackProps) {
    super(scope, id, props);

    applyConventions(props.foundation, 'data', this);

    const databaseSecurityGroup =
      props.databaseSecurityGroup ??
      (props.allowSelfManagedSecurityGroup
        ? new ec2.SecurityGroup(this, 'DataDatabaseSecurityGroup', {
            vpc: props.vpc,
            description: 'Data stack self-managed fallback security group for PostgreSQL access.',
            allowAllOutbound: false,
          })
        : undefined);

    if (
      props.allowSelfManagedSecurityGroup &&
      props.publicDatabaseAccess &&
      databaseSecurityGroup &&
      props.publicDatabaseAccessCidr
    ) {
      databaseSecurityGroup.addIngressRule(
        ec2.Peer.ipv4(props.publicDatabaseAccessCidr),
        ec2.Port.tcp(5432),
        'Allow PostgreSQL traffic from configured public CIDR range.',
      );
    }

    if (!databaseSecurityGroup) {
      throw new Error(
        'DataStack requires databaseSecurityGroup unless allowSelfManagedSecurityGroup is enabled.',
      );
    }

    const databaseSubnetType = props.publicDatabaseAccess ? ec2.SubnetType.PUBLIC : ec2.SubnetType.PRIVATE_ISOLATED;
    const databaseSubnetGroup = new rds.SubnetGroup(
      this,
      props.publicDatabaseAccess ? 'PublicProfileDatabaseSubnetGroup' : 'PrivateProfileDatabaseSubnetGroup',
      {
        description: 'Subnet group for the profile database instance.',
        vpc: props.vpc,
        vpcSubnets: {
          subnetType: databaseSubnetType,
        },
      },
    );

    databaseSubnetGroup.applyRemovalPolicy(RemovalPolicy.DESTROY);

    this.database = new rds.DatabaseInstance(this, 'ProfileDatabase', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_16,
      }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      vpc: props.vpc,
      subnetGroup: databaseSubnetGroup,
      securityGroups: [databaseSecurityGroup],
      allocatedStorage: 20,
      maxAllocatedStorage: 100,
      storageEncrypted: true,
      multiAz: false,
      publiclyAccessible: props.publicDatabaseAccess ?? false,
      deletionProtection: false,
      deleteAutomatedBackups: true,
      backupRetention: undefined,
      removalPolicy: RemovalPolicy.DESTROY,
      databaseName: 'profile_db',
      credentials: rds.Credentials.fromGeneratedSecret('profile_user'),
    });

    this.cvBucket = new s3.Bucket(this, 'ProfileCvBucket', {
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      autoDeleteObjects: true,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    new CfnOutput(this, 'DatabaseEndpointAddress', {
      value: this.database.instanceEndpoint.hostname,
      description: 'RDS PostgreSQL endpoint hostname for profile-service.',
    });

    new CfnOutput(this, 'DatabaseSecretArn', {
      value: this.database.secret!.secretArn,
      description: 'Secrets Manager ARN with generated PostgreSQL credentials.',
    });

    new CfnOutput(this, 'CvBucketName', {
      value: this.cvBucket.bucketName,
      description: 'S3 bucket name used for uploaded CV files.',
    });
  }
}