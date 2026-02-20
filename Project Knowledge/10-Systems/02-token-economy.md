# Token Economy

## Token Costs

| Action | Token Cost |
|--------|-----------|
| take_test | 1 token |
| generate_test | 5 tokens |

## Free Tokens

- **2 free tokens daily** (`DAILY_FREE_TOKENS` env var)
- Reset logic handled in `PaymentService`

## Purchasable Packages (via Stripe)

| Package | Tokens | Price |
|---------|--------|-------|
| starter_10 | 10 | $1.99 |
| popular_50 | 50 | $7.99 |
| premium_200 | 200 | $19.99 |

## Stripe Integration Flow

1. Client requests `GET /api/payments/token-packages`
2. Client selects package, sends `POST /api/payments/create-intent {package_id}`
3. Backend creates Stripe `PaymentIntent` with metadata (user_id, package_id, tokens)
4. Client completes payment with Stripe.js
5. Stripe webhook -> `handle_successful_payment()` -> credit tokens to user

## Token Balance

- Stored in `users.tokens` column
- Checked before each action via `can_perform_action()`
- Consumed atomically via `consume_tokens()`

## Related Documents

- [01-elo-rating-system.md](01-elo-rating-system.md) - Test attempts that consume tokens
- [03-content-moderation.md](03-content-moderation.md) - Moderation before test generation
- [04-audio-pipeline.md](04-audio-pipeline.md) - Audio generation during test creation
