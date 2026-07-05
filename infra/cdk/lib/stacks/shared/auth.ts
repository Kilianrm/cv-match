import { CfnOutput, RemovalPolicy, Stack, StackProps } from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';

import { applyConventions, FoundationConfig } from '../../../bin/conventions';

export interface AuthStackProps extends StackProps {
  foundation: FoundationConfig;
  localFrontendBaseUrl?: string;
  cognitoDomainPrefix?: string;
}

function sanitizeDomainPrefix(value: string): string {
  const sanitized = value
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-/, '')
    .replace(/-$/, '');

  if (!sanitized) {
    return 'cvmatch-dev-auth';
  }

  return sanitized.slice(0, 63).replace(/-$/, '') || 'cvmatch-dev-auth';
}

export class AuthStack extends Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly issuer: string;
  public readonly jwksUrl: string;
  public readonly authorizationEndpoint: string;
  public readonly tokenEndpoint: string;
  public readonly logoutEndpoint: string;
  public readonly hostedDomainName: string;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    applyConventions(props.foundation, 'auth', this);

    const localFrontendBaseUrl = (props.localFrontendBaseUrl ?? 'http://localhost:3000').replace(/\/$/, '');

    this.userPool = new cognito.UserPool(this, 'FrontendUserPool', {
      userPoolName: `${props.foundation.appName}-${props.foundation.stage}-users`,
      selfSignUpEnabled: true,
      signInAliases: {
        email: true,
      },
      autoVerify: {
        email: true,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      removalPolicy: RemovalPolicy.DESTROY,
    });

    this.userPoolClient = new cognito.UserPoolClient(this, 'FrontendUserPoolClient', {
      userPool: this.userPool,
      userPoolClientName: `${props.foundation.appName}-${props.foundation.stage}-web-client`,
      generateSecret: false,
      preventUserExistenceErrors: true,
      authFlows: {
        userSrp: true,
      },
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        callbackUrls: [`${localFrontendBaseUrl}/api/auth/callback`],
        logoutUrls: [localFrontendBaseUrl],
        scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
      },
      supportedIdentityProviders: [cognito.UserPoolClientIdentityProvider.COGNITO],
    });

    const accountSuffix = props.foundation.env.account?.slice(-6) ?? 'local';
    const computedPrefix = `${props.foundation.appName}-${props.foundation.stage}-${accountSuffix}`;
    const domainPrefix = sanitizeDomainPrefix(props.cognitoDomainPrefix ?? computedPrefix);

    const domain = this.userPool.addDomain('HostedUiDomain', {
      cognitoDomain: {
        domainPrefix,
      },
    });

    this.hostedDomainName = domain.baseUrl().replace(/^https?:\/\//, '');
    this.authorizationEndpoint = `${domain.baseUrl()}/oauth2/authorize`;
    this.tokenEndpoint = `${domain.baseUrl()}/oauth2/token`;
    this.logoutEndpoint = `${domain.baseUrl()}/logout`;
    this.issuer = `https://cognito-idp.${props.foundation.env.region}.amazonaws.com/${this.userPool.userPoolId}`;
    this.jwksUrl = `${this.issuer}/.well-known/jwks.json`;

    new CfnOutput(this, 'CognitoUserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID for CV Match frontend authentication.',
    });

    new CfnOutput(this, 'CognitoUserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito App Client ID (public PKCE client) for frontend auth flow.',
    });

    new CfnOutput(this, 'CognitoHostedDomain', {
      value: this.hostedDomainName,
      description: 'Cognito hosted domain name for OAuth endpoints.',
    });

    new CfnOutput(this, 'CognitoAuthorizationEndpoint', {
      value: this.authorizationEndpoint,
      description: 'Cognito OAuth2 authorization endpoint for frontend login redirect.',
    });

    new CfnOutput(this, 'CognitoTokenEndpoint', {
      value: this.tokenEndpoint,
      description: 'Cognito OAuth2 token endpoint for authorization code exchange.',
    });

    new CfnOutput(this, 'CognitoLogoutEndpoint', {
      value: this.logoutEndpoint,
      description: 'Cognito logout endpoint for Hosted UI sign-out.',
    });

    new CfnOutput(this, 'CognitoIssuer', {
      value: this.issuer,
      description: 'OIDC issuer URL used by gateway-service JWT verification.',
    });

    new CfnOutput(this, 'CognitoJwksUrl', {
      value: this.jwksUrl,
      description: 'JWKS URL used by gateway-service to verify Cognito JWT signatures.',
    });
  }
}
