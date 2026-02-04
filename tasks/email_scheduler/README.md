# Email Scheduler Lambda

AWS Lambda function for sending scheduled personalized email reflections to NeuroResolv users.

## Overview

This Lambda is triggered every hour by AWS EventBridge. It queries the NeuroResolv API to find users who should receive emails at the current hour (based on their timezone and preferences), then triggers the API to generate and send personalized emails.

## Files

- `handler.py` - Main Lambda handler
- `test_email_scheduler.py` - Local testing script

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `API_BASE_URL` | Base URL of the NeuroResolv API | `https://api.neuroresolv.com` |
| `API_KEY` | API key for authentication | `your-api-key` |

## Deployment

### 1. Create the Lambda Function

```bash
# Create deployment package
cd tasks/email_scheduler
zip -r email_scheduler.zip handler.py

# Create Lambda via AWS CLI
aws lambda create-function \
    --function-name neuroresolv-email-scheduler \
    --runtime python3.11 \
    --handler handler.handler \
    --zip-file fileb://email_scheduler.zip \
    --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
    --timeout 60 \
    --memory-size 256
```

### 2. Set Environment Variables

```bash
aws lambda update-function-configuration \
    --function-name neuroresolv-email-scheduler \
    --environment "Variables={API_BASE_URL=https://your-api-url.com,API_KEY=your-api-key}"
```

### 3. Create EventBridge Rule

```bash
# Create rule to trigger every hour
aws events put-rule \
    --name neuroresolv-email-scheduler-hourly \
    --schedule-expression "rate(1 hour)"

# Add Lambda as target
aws events put-targets \
    --rule neuroresolv-email-scheduler-hourly \
    --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT:function:neuroresolv-email-scheduler"

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
    --function-name neuroresolv-email-scheduler \
    --statement-id eventbridge-invoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:REGION:ACCOUNT:rule/neuroresolv-email-scheduler-hourly
```

## Local Testing

```bash
# Set environment variables
export API_BASE_URL=http://localhost:8000
export API_KEY=dev-api-key-12345

# Run the Lambda handler directly
python handler.py

# Run comprehensive tests
python test_email_scheduler.py
```

## Flow Diagram

```
EventBridge (hourly)
    |
    v
Lambda handler.py
    |
    v
GET /email/scheduled-users?utc_hour=X
    |
    v
API returns list of users for this hour
    |
    v
POST /email/send with user_ids
    |
    v
API generates content & sends via SES
```

## IAM Permissions

The Lambda execution role needs:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
```

Note: The Lambda doesn't need SES permissions directly - it calls the API which handles email sending.
