#!/usr/bin/env bash
# Deploy one commit to one Render service and wait until it is live (ADR-014).
#
#   render-deploy.sh <service-id> <commit-sha>
#
# Needs RENDER_API_KEY in the environment. Fails if the deploy ends in any
# status other than live, or if it is still running after the timeout, so the
# workflow goes red instead of reporting a deploy that never happened.
set -euo pipefail

service_id="$1"
commit="$2"
api="https://api.render.com/v1/services/$service_id/deploys"
auth="Authorization: Bearer $RENDER_API_KEY"

deploy_id=$(
  curl --silent --show-error --fail-with-body -X POST "$api" \
    -H "$auth" -H "Content-Type: application/json" \
    -d "{\"commitId\": \"$commit\", \"clearCache\": \"do_not_clear\"}" |
    jq -r .id
)
echo "deploy $deploy_id of $commit to $service_id"

# Free instances build slowly: 20 minutes, checked every 15 seconds.
for _ in $(seq 1 80); do
  status=$(curl --silent --show-error --fail "$api/$deploy_id" -H "$auth" | jq -r .status)
  case "$status" in
    live)
      echo "live"
      exit 0
      ;;
    build_failed | update_failed | pre_deploy_failed | canceled | deactivated)
      echo "::error::Render deploy $deploy_id ended as $status; check its logs in the dashboard"
      exit 1
      ;;
  esac
  echo "status: $status"
  sleep 15
done

echo "::error::Render deploy $deploy_id still not live after 20 minutes"
exit 1
