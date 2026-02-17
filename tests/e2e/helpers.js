/**
 * E2E Test Helpers for ArkWatch API
 *
 * Uses test_helper.py (via venv Python) to manage test user lifecycle.
 * The helper creates users with known verification codes, bypassing email.
 */
const { execSync } = require('child_process');
const path = require('path');
const crypto = require('crypto');

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const VENV_PYTHON = path.join(PROJECT_ROOT, 'venv', 'bin', 'python3');
const HELPER_SCRIPT = path.join(__dirname, 'test_helper.py');

/**
 * Generate a unique test email to avoid conflicts between test runs.
 */
function generateTestEmail(prefix = 'e2e') {
  const id = crypto.randomBytes(4).toString('hex');
  return `${prefix}-${id}@test.arkforge.fr`;
}

/**
 * Create a test user directly via Python helper.
 * Returns { api_key, verification_code }.
 */
function createTestUser(email) {
  const raw = execSync(
    `${VENV_PYTHON} ${HELPER_SCRIPT} create "${email}"`,
    { cwd: PROJECT_ROOT, encoding: 'utf-8', timeout: 10000 }
  );
  // Parse last line (skip any warnings like PII key message)
  const lines = raw.trim().split('\n');
  return JSON.parse(lines[lines.length - 1]);
}

/**
 * Clean up a test user and all associated data.
 */
function cleanupUser(email) {
  try {
    execSync(
      `${VENV_PYTHON} ${HELPER_SCRIPT} cleanup "${email}"`,
      { cwd: PROJECT_ROOT, encoding: 'utf-8', timeout: 10000 }
    );
  } catch {
    // Best-effort cleanup
  }
}

module.exports = { generateTestEmail, createTestUser, cleanupUser };
