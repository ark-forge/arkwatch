// @ts-check
const { test, expect } = require('@playwright/test');
const { generateTestEmail, createTestUser, cleanupUser } = require('./helpers');
const { execSync } = require('child_process');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const VENV_PYTHON = path.join(PROJECT_ROOT, 'venv', 'bin', 'python3');

/**
 * Create a verified test user (ready for watch operations).
 */
function createVerifiedUser() {
  const email = generateTestEmail('core');
  const user = createTestUser(email);
  // Verify email directly via Python
  execSync(
    `${VENV_PYTHON} -c "import sys; sys.path.insert(0, '${PROJECT_ROOT}'); from src.api.auth import verify_user_email; verify_user_email('${email}', '${user.verification_code}')"`,
    { cwd: PROJECT_ROOT, encoding: 'utf-8', timeout: 10000 }
  );
  return { email, apiKey: user.api_key };
}

/**
 * E2E Test: Core Flow
 * Create Watch → Verify creation → List → Update → Delete
 */
test.describe('Core Flow - Watch Management', () => {

  test('POST /api/v1/watches creates a new watch', async ({ request }) => {
    const { email, apiKey } = createVerifiedUser();
    try {
      const response = await request.post('/api/v1/watches', {
        headers: { 'X-API-Key': apiKey },
        data: {
          url: 'https://example.com',
          name: 'E2E Test Watch',
          check_interval: 86400,
        },
      });
      expect(response.status()).toBe(200);

      const watch = await response.json();
      expect(watch.id).toBeTruthy();
      expect(watch.name).toBe('E2E Test Watch');
      expect(watch.status).toBe('active');
      expect(watch.check_interval).toBeGreaterThanOrEqual(86400);
    } finally {
      cleanupUser(email);
    }
  });

  test('GET /api/v1/watches lists created watches', async ({ request }) => {
    const { email, apiKey } = createVerifiedUser();
    try {
      // Create a watch
      const createRes = await request.post('/api/v1/watches', {
        headers: { 'X-API-Key': apiKey },
        data: {
          url: 'https://httpbin.org/html',
          name: 'List Test Watch',
          check_interval: 86400,
        },
      });
      expect(createRes.status()).toBe(200);
      const created = await createRes.json();

      // List watches
      const listRes = await request.get('/api/v1/watches', {
        headers: { 'X-API-Key': apiKey },
      });
      expect(listRes.status()).toBe(200);

      const watches = await listRes.json();
      expect(Array.isArray(watches)).toBe(true);
      expect(watches.length).toBeGreaterThanOrEqual(1);

      const found = watches.find(w => w.id === created.id);
      expect(found).toBeTruthy();
      expect(found.name).toBe('List Test Watch');
    } finally {
      cleanupUser(email);
    }
  });

  test('GET /api/v1/watches/:id retrieves specific watch', async ({ request }) => {
    const { email, apiKey } = createVerifiedUser();
    try {
      const createRes = await request.post('/api/v1/watches', {
        headers: { 'X-API-Key': apiKey },
        data: {
          url: 'https://example.org',
          name: 'Get Test Watch',
          check_interval: 86400,
        },
      });
      const created = await createRes.json();

      const getRes = await request.get(`/api/v1/watches/${created.id}`, {
        headers: { 'X-API-Key': apiKey },
      });
      expect(getRes.status()).toBe(200);

      const watch = await getRes.json();
      expect(watch.id).toBe(created.id);
      expect(watch.name).toBe('Get Test Watch');
    } finally {
      cleanupUser(email);
    }
  });

  test('PATCH /api/v1/watches/:id updates a watch', async ({ request }) => {
    const { email, apiKey } = createVerifiedUser();
    try {
      const createRes = await request.post('/api/v1/watches', {
        headers: { 'X-API-Key': apiKey },
        data: {
          url: 'https://example.net',
          name: 'Update Test Watch',
          check_interval: 86400,
        },
      });
      expect(createRes.status()).toBe(200);
      const created = await createRes.json();

      const updateRes = await request.patch(`/api/v1/watches/${created.id}`, {
        headers: { 'X-API-Key': apiKey },
        data: { name: 'Updated Watch Name', status: 'paused' },
      });
      expect(updateRes.status()).toBe(200);

      const updated = await updateRes.json();
      expect(updated.name).toBe('Updated Watch Name');
      expect(updated.status).toBe('paused');
    } finally {
      cleanupUser(email);
    }
  });

  test('DELETE /api/v1/watches/:id removes a watch', async ({ request }) => {
    const { email, apiKey } = createVerifiedUser();
    try {
      const createRes = await request.post('/api/v1/watches', {
        headers: { 'X-API-Key': apiKey },
        data: {
          url: 'https://example.com/delete-me',
          name: 'Delete Test Watch',
          check_interval: 86400,
        },
      });
      const created = await createRes.json();

      const deleteRes = await request.delete(`/api/v1/watches/${created.id}`, {
        headers: { 'X-API-Key': apiKey },
      });
      expect(deleteRes.status()).toBe(200);
      expect((await deleteRes.json()).status).toBe('deleted');

      // Verify it's gone
      const getRes = await request.get(`/api/v1/watches/${created.id}`, {
        headers: { 'X-API-Key': apiKey },
      });
      expect(getRes.status()).toBe(404);
    } finally {
      cleanupUser(email);
    }
  });

  test('Unverified user cannot create watches', async ({ request }) => {
    const email = generateTestEmail('unverified');
    const user = createTestUser(email);

    try {
      const response = await request.post('/api/v1/watches', {
        headers: { 'X-API-Key': user.api_key },
        data: {
          url: 'https://example.com',
          name: 'Should Fail',
          check_interval: 86400,
        },
      });
      expect(response.status()).toBe(403);

      const body = await response.json();
      expect(body.detail).toContain('verified');
    } finally {
      cleanupUser(email);
    }
  });

  test('Watch not found returns 404', async ({ request }) => {
    const { email, apiKey } = createVerifiedUser();
    try {
      const response = await request.get('/api/v1/watches/nonexistent-id-12345', {
        headers: { 'X-API-Key': apiKey },
      });
      expect(response.status()).toBe(404);
    } finally {
      cleanupUser(email);
    }
  });

  test('Free tier enforces max 3 watches limit', async ({ request }) => {
    const { email, apiKey } = createVerifiedUser();
    try {
      // Create 3 watches (max for free tier)
      for (let i = 0; i < 3; i++) {
        const res = await request.post('/api/v1/watches', {
          headers: { 'X-API-Key': apiKey },
          data: {
            url: `https://example.com/limit-${i}`,
            name: `Limit Test ${i}`,
            check_interval: 86400,
          },
        });
        expect(res.status()).toBe(200);
      }

      // 4th watch should be rejected
      const overRes = await request.post('/api/v1/watches', {
        headers: { 'X-API-Key': apiKey },
        data: {
          url: 'https://example.com/over-limit',
          name: 'Over Limit Watch',
          check_interval: 86400,
        },
      });
      expect(overRes.status()).toBe(403);
    } finally {
      cleanupUser(email);
    }
  });
});
