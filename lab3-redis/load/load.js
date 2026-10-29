import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';
const cacheReads = new Counter('cache_reads');
const transactionWrites = new Counter('transaction_writes');
const failedRequests = new Rate('failed_requests');
const readDuration = new Trend('cashback_read_duration', true);

export const options = {
  scenarios: {
    cashback_reads: {
      executor: 'ramping-vus',
      exec: 'readCashback',
      startVUs: 0,
      stages: [
        { duration: '20s', target: 30 },
        { duration: '40s', target: 30 },
        { duration: '20s', target: 80 },
        { duration: '40s', target: 80 },
        { duration: '10s', target: 0 },
      ],
    },
    transactions: {
      executor: 'constant-arrival-rate',
      exec: 'writeTransaction',
      rate: 5,
      timeUnit: '1s',
      duration: '2m',
      preAllocatedVUs: 10,
      maxVUs: 30,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    'http_req_duration{scenario:cashback_reads}': ['p(95)<200'],
    'http_req_duration{scenario:transactions}': ['p(95)<500'],
  },
};

export function readCashback() {
  // A hot working set gives a meaningful cache hit ratio while still creating misses.
  const userId = 1 + Math.floor(Math.random() * 200);
  const response = http.get(`${baseUrl}/api/v1/users/${userId}/cashback`);
  const ok = check(response, { 'cashback read is 200': (r) => r.status === 200 });
  failedRequests.add(!ok);
  cacheReads.add(1);
  readDuration.add(response.timings.duration);
  sleep(0.05);
}

export function writeTransaction() {
  const userId = 1 + Math.floor(Math.random() * 200);
  const categories = ['cafe', 'taxi', 'grocery', 'other'];
  const category = categories[Math.floor(Math.random() * categories.length)];
  const body = JSON.stringify({
    user_id: userId,
    category,
    amount: 100 + Math.floor(Math.random() * 4900),
  });
  const response = http.post(`${baseUrl}/api/v1/transactions`, body, {
    headers: { 'Content-Type': 'application/json' },
  });
  const ok = check(response, { 'transaction is 200': (r) => r.status === 200 });
  failedRequests.add(!ok);
  transactionWrites.add(1);
  sleep(0.1);
}
