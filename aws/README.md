# AWS Lambdas (M1)

Deployed copies of the M1 Lambda sources, region us-east-1. Each function is a single-file `index.handler` (python3.12) using the shared `flight-lambda-role`.

| Folder | Function | How it is deployed |
|---|---|---|
| flight-save-subscription | `POST /subscribe` on HTTP API `flight-api` | inline CloudFormation stack of the same name |
| flight-list-subscriptions | `GET /subscriptions?email=` | inline CloudFormation stack of the same name |
| flight-parser-wrapper | EventBridge rule `flight-price-check` (every 30 min) | `s3://flight-config-<ACCOUNT_ID>/lambda/wrapper.zip` |
| flight-parser | fetches TWD + USD fares, enqueues matches to SQS `flight-fare-queue` | `lambda/parser.zip` |
| flight-fare-notification | SQS consumer, dedups on `notification_history`, emails via Resend | `lambda/notify.zip` |
| flight-seed | deploy helper: writes base64 bytes to S3, or joins parts (`assemble`) | inline CloudFormation stack |

`flight-routes.json` is the routes config read by the wrapper from the same bucket. The deployed function is the source of truth; update this folder when you redeploy.
