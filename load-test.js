import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 1000,              // 1000 virtual users
  duration: '10m',       // total test duration
};

export default function () {
  const payload = {
    shop_id: '3fa85f64-5717-4562-b3fc-2c963f66afa6',
    name: `Bouquet ${__VU}-${__ITER}`,
    description: 'Direct and gateway test',
    category: 'Hybrid',
    price: '12.99',
    quantity: '5',
  };

  const encodedPayload = Object.entries(payload)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    timeout: '30s',  // timeout to avoid hanging requests
  };

  // Gateway request
  const gatewayRes = http.post(
    'http://localhost:31051/api/inventory/items/',
    encodedPayload,
    params
  );

  // Direct service request
  const directRes = http.post(
    'http://localhost:8001/inventoryitems/',
    encodedPayload,
    params
  );

  check(gatewayRes, {
    'gateway status is 201': (r) => r.status === 201,
  });

  check(directRes, {
    'direct status is 201': (r) => r.status === 201,
  });

  sleep(1); // Pause 1 second to reduce port-forward connection overload
}
