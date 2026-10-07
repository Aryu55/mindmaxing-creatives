import test from 'node:test';
import assert from 'node:assert/strict';
import '../site/demos/logic.js';
const logic = globalThis.DemoLogic;
test('visitor assignment is repeatable and covers both variants', () => {
  assert.equal(logic.bucket('visitor-21'), logic.bucket('visitor-21'));
  assert.deepEqual(new Set(Array.from({length:100}, (_, i) => logic.bucket(`visitor-${i}`))), new Set(['A', 'B']));
});
test('failed event can retry, successful events cannot deliver twice', () => {
  const queue = logic.initialPipeline();
  const failed = logic.processEvent(queue, 'EVT-102');
  assert.equal(failed.find(x => x.id === 'EVT-102').status, 'retry');
  const delivered = logic.processEvent(failed, 'EVT-102');
  assert.equal(delivered.find(x => x.id === 'EVT-102').status, 'delivered');
  assert.deepEqual(logic.processEvent(delivered, 'EVT-102'), delivered);
  assert.equal(queue[1].status, 'queued');
});
test('cart clamps quantity, calculates threshold, and resets with a fresh value', () => {
  assert.deepEqual(logic.cart(2), {quantity:2, subtotal:980, shipping:60, total:1040, remaining:20});
  assert.equal(logic.cart(3).shipping, 0);
  assert.equal(logic.cart(-10).quantity, 0);
  assert.equal(logic.cart(200).quantity, 10);
  const changed = logic.cart(6);
  assert.notDeepEqual(changed, logic.cart());
  assert.equal(logic.cart().quantity, 1);
});
