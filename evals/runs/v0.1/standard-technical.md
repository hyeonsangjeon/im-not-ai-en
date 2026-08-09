This change adds a bounded retry mechanism for webhook delivery. The worker uses exponential backoff with full jitter, caps each delay at 15 minutes, and stops after 8 attempts. Retries are limited to 408, 429, and 5xx responses; other 4xx responses go directly to `dead_letter`.

One caveat: `Retry-After` may be either delta-seconds or an HTTP-date, but the current parser handles only delta-seconds. All 37 responses in our two-week sample from ExamplePay used delta-seconds, although the HTTP-date form is still possible. If the header is missing or malformed, we fall back to the computed delay.

I kept the parser small deliberately. The result is a resilient retry path that avoids retrying every failure. I’d rather add HTTP-date support with a fixture from the wild than guess at timezone behavior in this patch.
