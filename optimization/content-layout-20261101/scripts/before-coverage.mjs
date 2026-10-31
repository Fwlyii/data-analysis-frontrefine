// Convenience entry point for the frozen desktop baseline; never writes current evidence.
process.env.REVIEW_STAGE='before';
process.env.REVIEW_BASE=process.env.REVIEW_BASE||'http://127.0.0.1:8829/';
process.env.REVIEW_SIZES='pair';
await import('./coverage.mjs');
