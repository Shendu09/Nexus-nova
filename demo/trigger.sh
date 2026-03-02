#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
INFRA_STACK="flare-demo-infra"

# ---------------------------------------------------------------------------
# break / fix — real infrastructure demo (ECS + RDS network partition)
# ---------------------------------------------------------------------------

if [ "${1:-}" = "break" ] || [ "${1:-}" = "fix" ]; then
    RDS_SG=$(aws cloudformation describe-stacks \
        --stack-name "$INFRA_STACK" --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`RdsSecurityGroupId`].OutputValue' \
        --output text)
    ECS_SG=$(aws cloudformation describe-stacks \
        --stack-name "$INFRA_STACK" --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`EcsSecurityGroupId`].OutputValue' \
        --output text)

    if [ "$1" = "break" ]; then
        echo "=== Revoking RDS security group ingress (network partition) ==="
        aws ec2 revoke-security-group-ingress \
            --group-id "$RDS_SG" \
            --protocol tcp --port 5432 \
            --source-group "$ECS_SG" \
            --region "$REGION" 2>/dev/null && \
            echo "Done. ECS can no longer reach the database." || \
            echo "Rule already revoked (partition already active)."
        echo "Watch logs: aws logs tail /ecs/flare-demo --follow --region $REGION"
    else
        echo "=== Restoring RDS security group ingress ==="
        aws ec2 authorize-security-group-ingress \
            --group-id "$RDS_SG" \
            --protocol tcp --port 5432 \
            --source-group "$ECS_SG" \
            --region "$REGION" 2>/dev/null && \
            echo "Done. Database connectivity restored." || \
            echo "Rule already present (connectivity already restored)."
    fi
    exit 0
fi

# ---------------------------------------------------------------------------
# Lambda-based demo (simple, existing behavior)
# ---------------------------------------------------------------------------

DEMO_FUNCTION="${1:-flare-demo-failing}"
FLARE_FUNCTION="${2:-}"
INVOCATIONS="${3:-10}"
MODE="${4:-cascade}"

echo "=== Invoking demo function '$DEMO_FUNCTION' ${INVOCATIONS}x with mode=$MODE ==="
for i in $(seq 1 "$INVOCATIONS"); do
    echo "  Invocation $i/$INVOCATIONS..."
    aws lambda invoke \
        --function-name "$DEMO_FUNCTION" \
        --payload "{\"mode\": \"$MODE\", \"invocation\": $i}" \
        --cli-binary-format raw-in-base64-out \
        /dev/null 2>/dev/null || true
    sleep 2
done

echo ""
echo "=== Waiting 10s for CloudWatch Logs to propagate ==="
sleep 10

if [ -n "$FLARE_FUNCTION" ]; then
    echo "=== Invoking Flare function '$FLARE_FUNCTION' ==="
    aws lambda invoke \
        --function-name "$FLARE_FUNCTION" \
        --payload '{}' \
        --cli-binary-format raw-in-base64-out \
        /tmp/flare-output.json
    echo ""
    echo "=== Flare response ==="
    cat /tmp/flare-output.json
    echo ""

    TABLE_NAME="${5:-}"
    if [ -n "$TABLE_NAME" ]; then
        echo ""
        echo "=== Checking DynamoDB for incident record ==="
        aws dynamodb scan \
            --table-name "$TABLE_NAME" \
            --max-items 1 \
            --query 'Items[0].{id:incident_id.S,status:prefetch_status.S,alarm:alarm_name.S}' \
            --output table 2>/dev/null || echo "    (no incidents table or no records)"
    fi
else
    echo "No Flare function specified. Pass it as the second argument to trigger analysis."
    echo "Usage: $0 <demo-function> <flare-function> [invocations] [mode] [incidents-table]"
fi
