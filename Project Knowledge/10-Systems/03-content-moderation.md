# Content Moderation

## Overview

- **Endpoint**: `POST /api/tests/moderate`
- Uses OpenAI Moderation API via `AIService.moderate_content()`
- Checks: sexual, hate, violence, self-harm, etc.
- If flagged: records in `flagged_content`/`user_reports` table via `TestService.record_flagged_input()`
- Returns `{is_safe, flagged_categories}`
- Used before custom test creation with user-provided transcripts

## Related Documents

- [02-token-economy.md](02-token-economy.md) - Token costs for test generation
- [04-audio-pipeline.md](04-audio-pipeline.md) - Audio generated after moderation passes
- [05-language-support.md](05-language-support.md) - Language-specific content considerations
