/**
 * Simple Node.js test server
 */

const http = require('http');

const port = process.env.PORT || 3000;

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello from NPM test server!');
  console.log(`Request: ${req.method} ${req.url}`);
});

server.listen(port, () => {
  console.log(`Test server starting on port ${port}`);
});

process.on('SIGTERM', () => {
  console.log('Received SIGTERM, shutting down...');
  server.close(() => {
    process.exit(0);
  });
});
