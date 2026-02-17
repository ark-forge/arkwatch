// @ts-check
const { test, expect } = require('@playwright/test');
const { generateTestEmail, createTestUser, cleanupUser } = require('./helpers');

/**
 * E2E Test: Onboarding Flow
 * Landing → Register → Verify Email → Authenticated Access
 *
 * Note: /api/v1/auth/register is rate-limited to 3 calls/IP/hour.
 * Tests use createTestUser() (direct DB) where possible to avoid hitting the limit.
 * Only 1 test calls the register endpoint via API.
 */
test.describe('Onboarding Flow', () => {

  test('GET / returns API info (landing)', async ({ request }) => {
    const response = await request.get('/');
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.name).toBe('ArkWatch API');
    expect(body.status).toBe('running');
  });

  test('GET /health returns healthy', async ({ request }) => {
    const response = await request.get('/health');
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.status).toBe('healthy');
  });

  test('POST /api/v1/auth/register - full registration flow via API', async ({ request }) => {
    // This test covers multiple registration scenarios in one test
    // to minimize rate-limited API calls (max 3/IP/hour).
    const email = generateTestEmail('onboard');

    try {
      // 1) Successful registration
      const regRes = await request.post('/api/v1/auth/register', {
        data: {
          email,
          name: 'E2E Onboarding Test',
          privacy_accepted: true,
        },
      });
      expect(regRes.status()).toBe(200);

      const regBody = await regRes.json();
      expect(regBody.api_key).toMatch(/^ak_/);
      expect(regBody.email).toBe(email);
      expect(regBody.tier).toBe('free');
      expect(regBody.message).toContain('verification');

      // 2) Duplicate email should be rejected (uses 1 more rate limit slot)
      const dupRes = await request.post('/api/v1/auth/register', {
        data: { email, name: 'Duplicate', privacy_accepted: true },
      });
      expect(dupRes.status()).toBe(409);

      // 3) Missing privacy consent → pydantic 422 (doesn't consume rate limit)
      const privacyRes = await request.post('/api/v1/auth/register', {
        data: {
          email: 'no-privacy@test.arkforge.fr',
          name: 'No Privacy',
          privacy_accepted: false,
        },
      });
      expect(privacyRes.status()).toBe(422);
    } finally {
      cleanupUser(email);
    }
  });

  test('POST /api/v1/auth/verify-email verifies with correct code', async ({ request }) => {
    const email = generateTestEmail('verify');
    const user = createTestUser(email);

    try {
      const response = await request.post('/api/v1/auth/verify-email', {
        data: { email, code: user.verification_code },
      });
      expect(response.status()).toBe(200);

      const body = await response.json();
      expect(body.status).toBe('verified');
    } finally {
      cleanupUser(email);
    }
  });

  test('POST /api/v1/auth/verify-email rejects wrong code', async ({ request }) => {
    const email = generateTestEmail('badcode');
    createTestUser(email);

    try {
      const response = await request.post('/api/v1/auth/verify-email', {
        data: { email, code: '000000' },
      });
      expect(response.status()).toBe(400);
    } finally {
      cleanupUser(email);
    }
  });

  test('Full onboarding: Register → Verify → Authenticated access', async ({ request }) => {
    const email = generateTestEmail('full');
    const user = createTestUser(email);

    try {
      // Step 1: Verify email
      const verifyRes = await request.post('/api/v1/auth/verify-email', {
        data: { email, code: user.verification_code },
      });
      expect(verifyRes.status()).toBe(200);

      // Step 2: Authenticated access - list watches
      const watchesRes = await request.get('/api/v1/watches', {
        headers: { 'X-API-Key': user.api_key },
      });
      expect(watchesRes.status()).toBe(200);
      expect(Array.isArray(await watchesRes.json())).toBe(true);

      // Step 3: Create a watch (requires verified email)
      const createRes = await request.post('/api/v1/watches', {
        headers: { 'X-API-Key': user.api_key },
        data: {
          url: 'https://example.com',
          name: 'Full Onboarding Watch',
          check_interval: 86400,
        },
      });
      expect(createRes.status()).toBe(200);
      const watch = await createRes.json();
      expect(watch.id).toBeTruthy();
    } finally {
      cleanupUser(email);
    }
  });

  test('Unauthenticated access is rejected', async ({ request }) => {
    const response = await request.get('/api/v1/watches');
    expect(response.status()).toBe(401);
  });

  test('Invalid API key is rejected', async ({ request }) => {
    const response = await request.get('/api/v1/watches', {
      headers: { 'X-API-Key': 'ak_invalid_key_that_does_not_exist_12345' },
    });
    expect(response.status()).toBe(401);
  });
});
