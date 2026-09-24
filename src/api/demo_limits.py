"""Bound demo request bodies before multipart parsing, including chunked bodies."""

from starlette.responses import JSONResponse


class DemoBodyLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = self.max_bytes + 1
        body = bytearray()
        if declared <= self.max_bytes:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                part = message.get("body", b"")
                if len(body) + len(part) > self.max_bytes:
                    break
                body.extend(part)
                if not message.get("more_body", False):
                    delivered = False

                    async def bounded_receive():
                        nonlocal delivered
                        if not delivered:
                            delivered = True
                            return {"type": "http.request", "body": bytes(body), "more_body": False}
                        return await receive()

                    return await self.app(scope, bounded_receive, send)
        await JSONResponse(
            {"detail": "Request exceeds the demo byte limit."}, status_code=413
        )(scope, receive, send)
