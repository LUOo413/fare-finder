# AWS Lambdas (M1 + M2)

Deployed copies of the M1 Lambda sources, region us-east-1. Each function is a single-file `index.handler` (python3.12) using the shared `flight-lambda-role`.

| Folder | Function | How it is deployed |
|---|---|---|
| flight-save-subscription | `POST /subscribe` on HTTP API `flight-api` | created by the inline CloudFormation stack of the same name; since M2 the code is over the 4096-character inline limit, so it is updated from `lambda/save-subscription.zip` (do not re-apply the old stack template) |
| flight-list-subscriptions | `GET /subscriptions?email=` | inline CloudFormation stack of the same name |
| flight-parser-wrapper | EventBridge rule `flight-price-check` (every 30 min) | `s3://flight-config-<ACCOUNT_ID>/lambda/wrapper.zip` |
| flight-parser | fetches TWD + USD fares, enqueues matches to SQS `flight-fare-queue` | `lambda/parser.zip` |
| flight-fare-notification | SQS consumer, dedups on `notification_history`, emails via Resend | `lambda/notify.zip` |
| flight-seed | deploy helper: writes base64 bytes to S3, joins parts (`assemble`), or fetches a source URL and zips it as `index.py` (`url`) | inline CloudFormation stack |
| flight-ecpay-return | `POST /ecpay-return`: ECPay ReturnURL (first charge), verifies CheckMacValue, sets `active` + `current_period_end`, enqueues a welcome email | `lambda/ecpay-return.zip` |
| flight-ecpay-period | `POST /ecpay-period`: ECPay PeriodReturnURL (2nd charge on), extends `current_period_end`; 6 failures in a row -> `expired` | `lambda/ecpay-period.zip` |
| flight-ecpay-result | `ANY /ecpay-result`: ECPay OrderResultURL (browser POST), 302 to `/app?purchase=...` | `lambda/ecpay-result.zip` |
| flight-cancel-subscription | `POST /cancel`: ECPay CreditCardPeriodAction Cancel, sets `cancelled` (alerts continue until `current_period_end`), enqueues a cancel email | `lambda/cancel.zip` |
| flight-status-notification | SQS `flight-status-queue` consumer, sends the welcome/cancel email by `event_type` | `lambda/status-notify.zip` |

M2 subscription lifecycle (`subscription_status` on the `subscriptions` row): `pending_payment` -> `active` -> `cancelled` (grace) -> `expired`. `flight-save-subscription` returns ECPay's checkout form (HTML) unless the row is already paid, and the parser only alerts `active` rows and `cancelled` rows still inside their paid period. ECPay credentials and the monthly `amount` are in the `flight/ecpay` secret.

New code is deployed by pushing it to GitHub, then invoking `flight-seed` with `{"url": <raw.githubusercontent.com URL at a commit SHA>, "bucket", "key"}` and running `aws lambda update-function-code --s3-bucket ... --s3-key ...`. The zip is built deterministically, so its S3 ETag can be checked against a local build.

`flight-routes.json` is the routes config read by the wrapper from the same bucket. The deployed function is the source of truth; update this folder when you redeploy.
