import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

import { FoundationConfig } from '../../bin/conventions';

export interface EcsServiceLoggingProps {
  foundation: FoundationConfig;
  serviceName: string;
  streamPrefix?: string;
  retention?: logs.RetentionDays;
}

function getDefaultDevRetention(): logs.RetentionDays {
  return logs.RetentionDays.TWO_WEEKS;
}

export class EcsServiceLogging extends Construct {
  public readonly logGroup: logs.LogGroup;
  public readonly logDriver: ecs.LogDriver;

  constructor(scope: Construct, id: string, props: EcsServiceLoggingProps) {
    super(scope, id);

    this.logGroup = new logs.LogGroup(this, 'LogGroup', {
      logGroupName: `/${props.foundation.appName}/${props.foundation.stage}/services/${props.serviceName}`,
      retention: props.retention ?? getDefaultDevRetention(),
    });

    this.logDriver = ecs.LogDrivers.awsLogs({
      streamPrefix: props.streamPrefix ?? props.serviceName,
      logGroup: this.logGroup,
      mode: ecs.AwsLogDriverMode.NON_BLOCKING,
    });
  }
}