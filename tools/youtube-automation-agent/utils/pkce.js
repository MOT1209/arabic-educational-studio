// PKCE (RFC 7636, S256) for the loopback OAuth flows. The verifier never
// leaves this process; only its SHA-256 challenge goes to Google.
const crypto = require('crypto');

function createPkcePair() {
  const verifier = crypto.randomBytes(32).toString('base64url');
  const challenge = crypto.createHash('sha256').update(verifier).digest('base64url');
  return { verifier, challenge, method: 'S256' };
}

module.exports = { createPkcePair };
