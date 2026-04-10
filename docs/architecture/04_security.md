# Security Architecture

## Authentication & Authorization

### IAM Roles
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:GetLogEvents",
        "logs:DescribeLogGroups"
      ],
      "Resource": "arn:aws:logs:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*:*:foundation-model/*"
    }
  ]
}
```

### Secret Management
- Store credentials in Secrets Manager
- Rotate keys regularly
- Audit access logs
- Use least privilege

## Data Security

### In Transit
- TLS 1.2+ for all connections
- VPC endpoints for private access
- Signed AWS API calls
- Message authentication codes

### At Rest
- DynamoDB encryption enabled
- S3 server-side encryption
- KMS key management
- Regular key rotation

### Data Classification
- Public: Log summaries
- Internal: Full log content
- Confidential: Personal data redaction
- Restricted: PII handling per compliance

## Compliance

### Standards
- SOC 2 Type II
- ISO 27001
- HIPAA (if processing health data)
- GDPR (if processing EU data)

### Audit Trail
- CloudTrail for all API calls
- VPC Flow Logs for network
- Application logging
- Change management records

## Threat Mitigation

### Common Threats
- **Injection**: Input validation, parameterized queries
- **Unauthorized Access**: IAM policies, MFA
- **Data Breach**: Encryption, access controls
- **DDoS**: AWS Shield, rate limiting
- **Malware**: Code scanning, dependency audit

### Security Best Practices
- Least privilege principle
- Defense in depth
- Regular security reviews
- Penetration testing
- Incident response plan
