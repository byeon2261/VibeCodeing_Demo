import assert from 'node:assert/strict';
import test from 'node:test';

let fixtureId = 0;
async function fixture() {
  const scripts = [];
  globalThis.window = {};
  globalThis.document = {
    createElement: () => ({ remove() { this.removed = true; } }),
    head: { appendChild: script => scripts.push(script) },
  };
  const { loadKakaoMaps } = await import(`../src/kakaoMaps.js?fixture=${++fixtureId}`);
  function succeed(script) {
    window.kakao = { maps: { load(callback) { this.Map = class {}; callback(); } } };
    script.onload();
  }
  return { loadKakaoMaps, scripts, succeed };
}

test('concurrent popups share one SDK download and reopening reuses it', async () => {
  const { loadKakaoMaps, scripts, succeed } = await fixture();
  const first = loadKakaoMaps('public-js-key');
  const second = loadKakaoMaps('public-js-key');
  assert.equal(first, second);
  assert.equal(scripts.length, 1);
  succeed(scripts[0]);
  assert.equal(await first, window.kakao.maps);
  assert.equal(await loadKakaoMaps('public-js-key'), window.kakao.maps);
  assert.equal(scripts.length, 1);
  assert.equal(scripts[0].removed, undefined);
});

test('a failed SDK can be downloaded again on retry', async () => {
  const { loadKakaoMaps, scripts, succeed } = await fixture();
  const first = loadKakaoMaps('public-js-key');
  scripts[0].onerror();
  await assert.rejects(first);
  assert.equal(scripts[0].removed, true);
  const second = loadKakaoMaps('public-js-key');
  assert.equal(scripts.length, 2);
  succeed(scripts[1]);
  assert.equal(await second, window.kakao.maps);
});

test('a script response without the SDK rejects and allows retry', async () => {
  const { loadKakaoMaps, scripts, succeed } = await fixture();
  const first = loadKakaoMaps('public-js-key');
  scripts[0].onload();
  await assert.rejects(first);
  const second = loadKakaoMaps('public-js-key');
  succeed(scripts[1]);
  await second;
});

test('missing JavaScript key does not send a request', async () => {
  const { loadKakaoMaps, scripts } = await fixture();
  await assert.rejects(loadKakaoMaps(''));
  assert.equal(scripts.length, 0);
});
