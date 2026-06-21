import { CfnOutput, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { applyConventions, FoundationConfig } from '../../bin/conventions';

export interface BoundaryStackProps extends StackProps {
  foundation: FoundationConfig;
}

export class ServicesStack extends Stack {
  constructor(scope: Construct, id: string, props: BoundaryStackProps) {
    super(scope, id, props);

    applyConventions(props.foundation, 'services', this);

    new CfnOutput(this, 'Boundary', {
      value: 'services',
      description: 'Stack boundary reserved for service runtime resources.',
    });
  }
}
