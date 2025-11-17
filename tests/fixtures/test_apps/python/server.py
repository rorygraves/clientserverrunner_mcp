"""Simple Python test server."""

import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class SimpleHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler."""

    def do_GET(self) -> None:
        """Handle GET requests."""
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Hello from test server!")

    def log_message(self, format: str, *args: tuple) -> None:
        """Log requests to stdout."""
        sys.stdout.write(f"{self.address_string()} - {format % args}\n")
        sys.stdout.flush()


def run_server(port: int = 8888) -> None:
    """Run the test server.

    Args:
        port: Port to listen on
    """
    server = HTTPServer(("localhost", port), SimpleHandler)
    print(f"Test server starting on port {port}")
    sys.stdout.flush()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    run_server(port)
