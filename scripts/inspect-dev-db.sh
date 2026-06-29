#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${APP_NAME:-cv-match}"
STAGE="${STAGE:-dev}"
REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${STACK_NAME:-${APP_NAME}-${STAGE}-data}"
LIMIT="${LIMIT:-20}"
TABLE="${TABLE:-}"
COUNTS_ONLY="false"

print_help() {
  cat <<'EOF'
Usage:
  ./scripts/inspect-dev-db.sh [--table <name>] [--limit <n>] [--counts-only]

Environment variables:
  APP_NAME     Stack prefix (default: cv-match)
  STAGE        Environment stage (default: dev)
  AWS_REGION   AWS region (default: us-east-1)
  STACK_NAME   CF stack name (default: <app>-<stage>-data)
  TABLE        Table to preview (optional)
  LIMIT        Preview row limit (default: 20)

Examples:
  ./scripts/inspect-dev-db.sh
  ./scripts/inspect-dev-db.sh --counts-only
  ./scripts/inspect-dev-db.sh --table countries --limit 10
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_help
      exit 0
      ;;
    --table)
      TABLE="${2:-}"
      shift 2
      ;;
    --limit)
      LIMIT="${2:-}"
      shift 2
      ;;
    --counts-only)
      COUNTS_ONLY="true"
      shift
      ;;
    *)
      echo "Unsupported argument: $1" >&2
      print_help >&2
      exit 1
      ;;
  esac
done

if ! [[ "$LIMIT" =~ ^[0-9]+$ ]]; then
  echo "LIMIT must be a non-negative integer." >&2
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required" >&2
  exit 1
fi

DB_ENDPOINT="$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs[?OutputKey=='DatabaseEndpointAddress'].OutputValue" \
  --output text)"

DB_SECRET_ARN="$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs[?OutputKey=='DatabaseSecretArn'].OutputValue" \
  --output text)"

if [[ -z "${DB_ENDPOINT}" || "${DB_ENDPOINT}" == "None" ]]; then
  echo "DatabaseEndpointAddress output not found in stack ${STACK_NAME}" >&2
  exit 1
fi

if [[ -z "${DB_SECRET_ARN}" || "${DB_SECRET_ARN}" == "None" ]]; then
  echo "DatabaseSecretArn output not found in stack ${STACK_NAME}" >&2
  exit 1
fi

SECRET_JSON="$(aws secretsmanager get-secret-value \
  --secret-id "${DB_SECRET_ARN}" \
  --region "${REGION}" \
  --query SecretString \
  --output text)"

echo "[inspect-db] stack=${STACK_NAME} region=${REGION} endpoint=${DB_ENDPOINT}"

python3 - <<'PY' "${SECRET_JSON}" "${DB_ENDPOINT}" "${TABLE}" "${LIMIT}" "${COUNTS_ONLY}"
import json
import sys

secret_json = sys.argv[1]
host = sys.argv[2]
table = sys.argv[3].strip()
limit = int(sys.argv[4])
counts_only = sys.argv[5].lower() == "true"

try:
    from psycopg import connect
    from psycopg import sql
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "psycopg is required. Install with: python3 -m pip install --user --break-system-packages 'psycopg[binary]==3.3.4'"
    ) from exc

secret = json.loads(secret_json)
username = secret["username"]
password = secret["password"]
port = secret.get("port", 5432)
dbname = secret.get("dbname", "profile_db")

dsn = f"postgresql://{username}:{password}@{host}:{port}/{dbname}"

with connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )
        tables = [row[0] for row in cur.fetchall()]

        print("\nTables:")
        for t in tables:
            print(f" - {t}")

        print("\nRow counts:")
        for t in tables:
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}") .format(sql.Identifier(t)))
            count = cur.fetchone()[0]
            print(f" - {t}: {count}")

        if counts_only:
            sys.exit(0)

        if table:
            if table not in tables:
                raise RuntimeError(f"Table '{table}' not found in public schema")

            print(f"\nPreview rows from {table} (limit {limit}):")
            cur.execute(sql.SQL("SELECT * FROM {} LIMIT {}") .format(sql.Identifier(table), sql.Literal(limit)))
            rows = cur.fetchall()

            if not rows:
                print(" - (no rows)")
            else:
                col_names = [desc.name for desc in cur.description]
                print(" - columns:", ", ".join(col_names))
                for row in rows:
                    print(" -", row)
PY
