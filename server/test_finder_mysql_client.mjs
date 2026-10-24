import {test, afterEach, mock} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readMySQLState, writeMySQLState} from './finder_mysql_client.mjs';

const env = {FINDER_MYSQL_API_ORIGIN: 'https://finder.example', FINDER_MYSQL_API_TOKEN: 'm'.repeat(48)};
const state = () => ({revision: 'r1', department: 'meat', items: [{upc: '0000123', cost: null, quantity: 0}],
  files: [], movements: [], posEvents: [], priceEvents: [], ohSnapshots: [], history: [{name: '海鮮'}]});
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
function verifiedResponse(value) {
  const body = JSON.stringify(value), sha = hash(body);
  return new Response(body, {headers: {ETag: `"${sha}"`, 'X-Content-SHA256': sha}});
}
afterEach(() => mock.restoreAll());

test('read preserves complete state and supplies exact storage version', async () => {
  mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(String(url), 'https://finder.example/v1/departments/meat/state');
    assert.equal(options.redirect, 'error');
    assert.equal(options.headers.Authorization, 'Bearer ' + env.FINDER_MYSQL_API_TOKEN);
    return verifiedResponse(state());
  });
  const result = await readMySQLState(env, 'meat');
  assert.deepEqual(result.state, state());
  assert.equal(result.condition.etagMatches, hash(JSON.stringify(state())));
});

test('corrupt reads and incomplete states cannot become authoritative', async () => {
  mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(state()), {
    headers: {ETag: '"' + '0'.repeat(64) + '"', 'X-Content-SHA256': '0'.repeat(64)}}));
  await assert.rejects(readMySQLState(env, 'meat'), /checksum/);
  mock.restoreAll();
  mock.method(globalThis, 'fetch', async () => verifiedResponse({revision: 'r1'}));
  await assert.rejects(readMySQLState(env, 'meat'), /complete state/);
});

test('write verifies acknowledged exact bytes and does not mutate source', async () => {
  const value = state(), before = structuredClone(value), etag = 'a'.repeat(64);
  mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(options.method, 'PUT');
    assert.equal(options.redirect, 'error');
    assert.equal(options.headers['If-Match'], `"${etag}"`);
    const sha = hash(options.body);
    assert.equal(options.headers['X-Content-SHA256'], sha);
    assert.deepEqual(JSON.parse(new TextDecoder().decode(options.body)), value);
    return new Response(JSON.stringify({saved: true, sha256: sha}), {headers: {ETag: `"${sha}"`}});
  });
  assert.deepEqual(await writeMySQLState(env, 'meat', value, {etagMatches: etag}), {etag: hash(JSON.stringify(value))});
  assert.deepEqual(value, before);
});

test('new import is create-only and conflict asks caller to reload', async () => {
  mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(options.headers['If-None-Match'], '*');
    assert.equal(options.headers['If-Match'], undefined);
    return new Response('', {status: 409});
  });
  assert.equal(await writeMySQLState(env, 'meat', state(), {createOnly: true}), null);
});

test('failed or unverified save never returns saved', async () => {
  for (const response of [new Response('', {status: 503}), new Response('{"saved":true,"sha256":"wrong"}')]) {
    mock.method(globalThis, 'fetch', async () => response);
    await assert.rejects(writeMySQLState(env, 'meat', state(), {createOnly: true}), /unavailable|not verified/);
    mock.restoreAll();
  }
});

test('invalid destinations, scope, credentials and conditions send no request', async () => {
  const fetch = mock.method(globalThis, 'fetch', async () => {throw new Error('unexpected network request');});
  for (const origin of ['http://finder.example', 'https://finder.example/path', 'https://name:password@finder.example', 'https://finder.example/?x=y']) {
    await assert.rejects(readMySQLState({...env, FINDER_MYSQL_API_ORIGIN: origin}, 'meat'), /origin/);
  }
  await assert.rejects(readMySQLState(env, 'seafood'), /department/);
  await assert.rejects(readMySQLState({...env, FINDER_MYSQL_API_TOKEN: 'short'}, 'meat'), /credential/);
  for (const condition of [undefined, {createOnly: true, etagMatches: 'a'.repeat(64)}, {etagMatches: 'bad'}]) {
    await assert.rejects(writeMySQLState(env, 'meat', state(), condition), /exact read version/);
  }
  await assert.rejects(writeMySQLState(env, 'meat', {...state(), overflow: Infinity}, {createOnly: true}), /Non-finite/);
  assert.equal(fetch.mock.callCount(), 0);
});

test('oversized response is cancelled', async () => {
  let cancelled = false;
  mock.method(globalThis, 'fetch', async () => new Response(new ReadableStream({
    pull(controller) {controller.enqueue(new Uint8Array(16 * 1024 * 1024 + 1));},
    cancel() {cancelled = true;}
  })));
  await assert.rejects(readMySQLState(env, 'meat'), /supported size/);
  assert.equal(cancelled, true);
});
