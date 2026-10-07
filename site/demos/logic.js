(function (root) {
  'use strict';
  root.DemoLogic = {
    bucket(value) {
      let hash = 2166136261;
      for (const character of String(value).trim()) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
      return ((hash >>> 0) % 100) < 50 ? 'A' : 'B';
    },
    initialPipeline() { return [{id:'EVT-101', label:'Order received', status:'queued', attempts:0}, {id:'EVT-102', label:'Dispatch notification', status:'queued', attempts:0}, {id:'EVT-103', label:'Delivery follow-up', status:'queued', attempts:0}]; },
    processEvent(queue, id) {
      return queue.map(event => event.id !== id || event.status === 'delivered' ? {...event} : {...event, attempts:event.attempts + 1, status:event.id === 'EVT-102' && event.attempts === 0 ? 'retry' : 'delivered'});
    },
    cart(value = 1) {
      const quantity = Math.max(0, Math.min(10, Math.floor(Number(value) || 0))), subtotal = quantity * 490;
      const shipping = subtotal === 0 || subtotal >= 1000 ? 0 : 60;
      return {quantity, subtotal, shipping, total:subtotal + shipping, remaining:Math.max(0, 1000-subtotal)};
    }
  };
})(globalThis);
