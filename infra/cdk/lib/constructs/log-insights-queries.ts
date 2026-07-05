import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface LogInsightsQuery {
  name: string;
  queryString: string;
}

export interface ServiceLogInsightsQueriesProps {
  appName: string;
  stage: string;
  serviceName: string;
  logGroupNames: string[];
  queries: LogInsightsQuery[];
}

export class ServiceLogInsightsQueries extends Construct {
  constructor(scope: Construct, id: string, props: ServiceLogInsightsQueriesProps) {
    super(scope, id);

    props.queries.forEach((query, index) => {
      new logs.CfnQueryDefinition(this, `Query${index + 1}`, {
        name: `${props.appName}/${props.stage}/${props.serviceName}/${query.name}`,
        logGroupNames: props.logGroupNames,
        queryString: query.queryString,
      });
    });
  }
}

export function createStandardServiceQueries(serviceName: string): LogInsightsQuery[] {
  const commonQueries: LogInsightsQuery[] = [
    {
      name: 'errors-last-24h',
      queryString: [
        'fields @timestamp, level, message, event, request_id, trace_id, path, status_code',
        ' | filter level = "ERROR" or status_code >= 500',
        ' | sort @timestamp desc',
        ' | limit 200',
      ].join('\n'),
    },
    {
      name: 'slow-requests',
      queryString: [
        'fields @timestamp, event, method, path, status_code, duration_ms, request_id, trace_id',
        ' | filter event = "request_complete" and duration_ms >= 800',
        ' | sort duration_ms desc',
        ' | limit 200',
      ].join('\n'),
    },
  ];

  if (serviceName === 'gateway-service') {
    return [
      ...commonQueries,
      {
        name: 'downstream-profile-calls',
        queryString: [
          'fields @timestamp, dependency, dependency_method, dependency_path, dependency_status_code, dependency_duration_ms, request_id, trace_id',
          ' | filter event = "dependency_call" and dependency = "profile-service"',
          ' | sort @timestamp desc',
          ' | limit 200',
        ].join('\n'),
      },
    ];
  }

  if (serviceName === 'profile-service') {
    return [
      ...commonQueries,
      {
        name: 'cv-operations',
        queryString: [
          'fields @timestamp, event, user_id, storage_key, size_bytes, request_id, trace_id',
          ' | filter event in ["cv_upload", "cv_delete", "s3_upload", "s3_delete"]',
          ' | sort @timestamp desc',
          ' | limit 200',
        ].join('\n'),
      },
    ];
  }

  return commonQueries;
}