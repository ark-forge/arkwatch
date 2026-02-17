// @ts-check
const { test, expect } = require('@playwright/test');
const { generateTestEmail, createTestUser, cleanupUser } = require('./helpers');
const { execSync } = require('child_process');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const VENV_PYTHON = path.join(PROJECT_ROOT, 'venv', 'bin', 'python3');

/**
 * Create a verified test user (ready for all API operations).
 */
function createVerifiedUser() {
  const email = generateTestEmail('rgpd');
  const user = createTestUser(email);
  execSync(
    `${VENV_PYTHON} -c "import sys; sys.path.insert(0, '${PROJECT_ROOT}'); from src.api.auth import verify_user_email; verify_user_email('${email}', '${user.verification_code}')"`,
    { cwd: PROJECT_ROOT, encoding: 'utf-8', timeout: 10000 }
  );
  return { email, apiKey: user.api_key };
}

/**
 * E2E Test: RGPD Compliance
 * Data export → Account update → Account deletion → Verify data erased
 */
test.describe('RGPD Compliance', () => {

  test('GET /privacy returns privacy policy', async ({ request }) => {
    const response = await request.get('/privacy');
    expect(response.status()).toBe(200);
  });

  test('GET /api/v1/auth/account/data exports user data (Art. 15)', async ({ request }) => {
    const { email, apiKey } = createVerifiedUser();

    try {
      // Create a watch to have some data
      await request.post('/api/v1/watches', {
        headers: { 'X-API-Key': apiKey },
        data: {
          url: 'https://example.com/rgpd-test',
          name: 'RGPD Export Test',
          check_interval: 86400,
        },
      });

      // Export data
      const response = await request.get('/api/v1/auth/account/data', {
        headers: { 'X-API-Key': apiKey },
      });
      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data.account).toBeTruthy();
      expect(data.account.email).toBe(email);
      expect(data.watches).toBeTruthy();
      expect(Array.isArray(data.watches)).toBe(true);
      expect(data.watches.length).toBeGreaterThanOrEqual(1);
      expect(data.privacy_policy).toContain('arkforge.fr');
      expect(data.message).toContain('GDPR');
    } finally {
      cleanupUser(email);
    }
  });

  test('PATCH /api/v1/auth/account updates user name (Art. 16)', async ({ request }) => {
    const email = generateTestEmail('rgpd-update');
    const user = createTestUser(email);

    try {
      const response = await request.patch('/api/v1/auth/account', {
        headers: { 'X-API-Key': user.api_key },
        data: { name: 'Updated RGPD Name' },
      });
      expect(response.status()).toBe(200);

      const body = await response.json();
      expect(body.status).toBe('updated');
      expect(body.updated_fields).toContain('name');
    } finally {
      cleanupUser(email);
    }
  });

  test('PATCH /api/v1/auth/account rejects empty update', async ({ request }) => {
    const email = generateTestEmail('rgpd-empty');
    const user = createTestUser(email);

    try {
      const response = await request.patch('/api/v1/auth/account', {
        headers: { 'X-API-Key': user.api_key },
        data: {},
      });
      expect(response.status()).toBe(400);
    } finally {
      cleanupUser(email);
    }
  });

  test('DELETE /api/v1/auth/account deletes all user data (Art. 17)', async ({ request }) => {
    const { email, apiKey } = createVerifiedUser();

    // Create a watch (so there's data to delete)
    const watchRes = await request.post('/api/v1/watches', {
      headers: { 'X-API-Key': apiKey },
      data: {
        url: 'https://example.com/to-delete',
        name: 'Delete Me Watch',
        check_interval: 86400,
      },
    });
    expect(watchRes.status()).toBe(200);

    // Delete account
    const deleteRes = await request.delete('/api/v1/auth/account', {
      headers: { 'X-API-Key': apiKey },
    });
    expect(deleteRes.status()).toBe(200);

    const body = await deleteRes.json();
    expect(body.status).toBe('deleted');
    expect(body.email).toBe(email);
    expect(body.message).toContain('permanently deleted');

    // Verify: API key no longer works
    const verifyRes = await request.get('/api/v1/watches', {
      headers: { 'X-API-Key': apiKey },
    });
    expect(verifyRes.status()).toBe(401);
  });

  test('Unauthenticated account deletion is rejected', async ({ request }) => {
    // No X-API-Key header → should get 401
    const response = await request.delete('/api/v1/auth/account', {
      headers: { 'X-API-Key': '' },
    });
    expect(response.status()).toBe(401);
  });

  test('Full RGPD lifecycle: Create → Use → Export → Delete → Verify erasure', async ({ request }) => {
    const { email, apiKey } = createVerifiedUser();

    // Step 1: Create watches (use the service)
    const w1 = await request.post('/api/v1/watches', {
      headers: { 'X-API-Key': apiKey },
      data: {
        url: 'https://example.com/rgpd-1',
        name: 'RGPD Lifecycle Watch 1',
        check_interval: 86400,
      },
    });
    expect(w1.status()).toBe(200);

    const w2 = await request.post('/api/v1/watches', {
      headers: { 'X-API-Key': apiKey },
      data: {
        url: 'https://example.com/rgpd-2',
        name: 'RGPD Lifecycle Watch 2',
        check_interval: 86400,
      },
    });
    expect(w2.status()).toBe(200);

    // Step 2: Export data (Art. 15) - verify watches are included
    const exportRes = await request.get('/api/v1/auth/account/data', {
      headers: { 'X-API-Key': apiKey },
    });
    expect(exportRes.status()).toBe(200);
    const exportData = await exportRes.json();
    expect(exportData.watches.length).toBe(2);

    // Step 3: Delete account (Art. 17)
    const deleteRes = await request.delete('/api/v1/auth/account', {
      headers: { 'X-API-Key': apiKey },
    });
    expect(deleteRes.status()).toBe(200);
    expect((await deleteRes.json()).status).toBe('deleted');

    // Step 4: Verify complete erasure - API key should be invalid
    const authCheck = await request.get('/api/v1/watches', {
      headers: { 'X-API-Key': apiKey },
    });
    expect(authCheck.status()).toBe(401);

    // Step 5: Re-registration with same email should work (data truly deleted)
    const reUser = createTestUser(email);
    expect(reUser.api_key).toMatch(/^ak_/);
    cleanupUser(email);
  });
});
