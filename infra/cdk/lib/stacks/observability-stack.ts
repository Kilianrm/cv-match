import { CfnOutput, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { applyConventions, FoundationConfig } from '../../bin/conventions';

export interface BoundaryStackProps extends StackProps {
  foundation: FoundationConfig;
}

export class ObservabilityStack extends Stack {
  constructor(scope: Construct, id: string, props: BoundaryStackProps) {
    super(scope, id, props);

    applyConventions(props.foundation, 'observability', this);

    new CfnOutput(this, 'Boundary', {
      value: 'observability',
      description: 'Optional boundary for dashboards, alarms, and log retention.',
    });
  }
}
