import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 100, // Number of virtual users
  duration: '10m', // Duration of test
};

export default function () {
  const url = 'http://localhost:8080/api/inventory/items/';

  const payload = {
    shop_id: '3fa85f64-5717-4562-b3fc-2c963f66afa6',
    name: 'Test Bouquet',
    description: 'Load test flower set',
    category: 'Stress',
    price: '15.99',
    quantity: '10',
  };

  const formData = {
    'shop_id': payload.shop_id,
    'name': payload.name,
    'description': payload.description,
    'category': payload.category,
    'price': payload.price,
    'quantity': payload.quantity,
  };

  const res = http.post(url, formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  check(res, {
    'status is 201': (r) => r.status === 201,
  });

  sleep(1);
}
