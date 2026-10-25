// Server-only adapter. No credential or database URL belongs in browser code.
// Existing Sites can retain their parsing/calculations and change state storage.
const limit = 16 * 1024 * 1024;
function validateState(state, department) {
  if (!state || typeof state !== 'object' || Array.isArray(state) ||
      typeof state.revision !== 'string' || !state.revision.length || state.revision.length > 128 ||
      ['items', 'files', 'movements', 'posEvents', 'priceEvents', 'ohSnapshots'].some(key => !Array.isArray(state[key])) ||
      (state.department !== undefined && state.department !== department))
    throw new Error('A complete state for the correct department is required');
  return state;
}
function endpoint(env, department) {
  if (!['meat', 'produce'].includes(department)) throw new Error('Unknown department');
  const url = new URL(env.FINDER_MYSQL_API_ORIGIN || 'https://not-configured.invalid');
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.pathname !== '/' || !env.FINDER_MYSQL_API_ORIGIN)
    throw new Error('Configure a private server-side MySQL API origin');
  if (!env.FINDER_MYSQL_API_TOKEN || env.FINDER_MYSQL_API_TOKEN.length < 40) throw new Error('MySQL API credential is missing');
  return new URL(`/v1/departments/${department}/state`, url);
}
async function digest(bytes) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(b => b.toString(16).padStart(2, '0')).join('');
}
async function boundedBytes(response) {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('MySQL returned an empty response');
  const chunks = []; let size = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read(); if (done) break;
      size += value.byteLength;
      if (size > limit) throw new Error('MySQL response exceeds the supported size');
      chunks.push(value);
    }
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) {bytes.set(chunk, offset); offset += chunk.byteLength;}
  return bytes;
}
export async function readMySQLState(env, department) {
  const response = await fetch(endpoint(env, department), {redirect: 'error', cache: 'no-store',
    headers: {Authorization: 'Bearer ' + env.FINDER_MYSQL_API_TOKEN}, signal: AbortSignal.timeout(20000)});
  if (!response.ok) throw new Error(`MySQL state unavailable (${response.status}); retained data must not be replaced`);
  const bytes = await boundedBytes(response), sha256 = await digest(bytes);
  if (response.headers.get('ETag') !== `"${sha256}"` || response.headers.get('X-Content-SHA256') !== sha256)
    throw new Error('MySQL state checksum did not verify');
  const state = validateState(JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes)), department);
  return {state, condition: {etagMatches: sha256}};
}
export async function writeMySQLState(env, department, state, condition) {
  const url = endpoint(env, department);
  validateState(state, department);
  const bytes = new TextEncoder().encode(JSON.stringify(state, (key, value) => {
    if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('Non-finite state numbers cannot be saved');
    return value;
  }));
  if (bytes.byteLength > limit) throw new Error('State exceeds the supported size; save was not sent');
  const sha256 = await digest(bytes), headers = {Authorization: 'Bearer ' + env.FINDER_MYSQL_API_TOKEN,
    'Content-Type': 'application/json', 'X-Content-SHA256': sha256};
  if (condition?.etagMatches && /^[a-f0-9]{64}$/.test(condition.etagMatches) && condition.createOnly !== true) headers['If-Match'] = `"${condition.etagMatches}"`;
  else if (condition?.createOnly === true && condition.etagMatches === undefined) headers['If-None-Match'] = '*';
  else throw new Error('An exact read version is required before saving');
  const response = await fetch(url, {method: 'PUT', headers, body: bytes,
    redirect: 'error', signal: AbortSignal.timeout(20000)});
  if (response.status === 409) return null; // Caller reloads and reapplies its operation.
  if (!response.ok) throw new Error(`MySQL save unavailable (${response.status}); read current state before retrying`);
  const result = JSON.parse(new TextDecoder().decode(await boundedBytes(response)));
  if (result.saved !== true || result.sha256 !== sha256 || response.headers.get('ETag') !== `"${sha256}"`)
    throw new Error('MySQL save was not verified');
  return {etag: sha256};
}
