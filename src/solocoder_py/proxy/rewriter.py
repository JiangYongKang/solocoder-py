from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Pattern

from .exceptions import RewriterError
from .models import Request, Response


class RequestRewriter(ABC):
    @abstractmethod
    def rewrite(self, request: Request) -> Request:
        ...


class ResponseRewriter(ABC):
    @abstractmethod
    def rewrite(self, response: Response, request: Request) -> Response:
        ...


@dataclass
class UrlRewriteRule:
    pattern: Pattern[str]
    replacement: str
    method: Optional[str] = None

    def matches(self, request: Request) -> bool:
        if self.method and request.method != self.method:
            return False
        return self.pattern.search(request.url) is not None


class UrlRewriter(RequestRewriter):
    def __init__(self, rules: Optional[List[UrlRewriteRule]] = None) -> None:
        self._rules: List[UrlRewriteRule] = rules or []

    def add_rule(self, pattern: str, replacement: str, method: Optional[str] = None) -> "UrlRewriter":
        self._rules.append(
            UrlRewriteRule(
                pattern=re.compile(pattern),
                replacement=replacement,
                method=method,
            )
        )
        return self

    def rewrite(self, request: Request) -> Request:
        try:
            for rule in self._rules:
                if rule.matches(request):
                    new_url = rule.pattern.sub(rule.replacement, request.url)
                    request = request.copy()
                    request.url = new_url
                    return request
            return request
        except Exception as e:
            raise RewriterError(f"URL rewrite failed: {e}") from e


class RequestHeaderRewriter(RequestRewriter):
    def __init__(
        self,
        add_headers: Optional[Dict[str, str]] = None,
        remove_headers: Optional[List[str]] = None,
        replace_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self._add = dict(add_headers or {})
        self._remove = list(remove_headers or [])
        self._replace = dict(replace_headers or {})

    def add_header(self, name: str, value: str) -> "RequestHeaderRewriter":
        self._add[name] = value
        return self

    def remove_header(self, name: str) -> "RequestHeaderRewriter":
        self._remove.append(name)
        return self

    def replace_header(self, name: str, value: str) -> "RequestHeaderRewriter":
        self._replace[name] = value
        return self

    def rewrite(self, request: Request) -> Request:
        try:
            modified = request.copy()
            for name in self._remove:
                modified.headers.pop(name, None)
            for name, value in self._replace.items():
                if name in modified.headers:
                    modified.headers[name] = value
            for name, value in self._add.items():
                modified.headers[name] = value
            return modified
        except Exception as e:
            raise RewriterError(f"Request header rewrite failed: {e}") from e


class ResponseHeaderRewriter(ResponseRewriter):
    def __init__(
        self,
        add_headers: Optional[Dict[str, str]] = None,
        remove_headers: Optional[List[str]] = None,
        replace_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self._add = dict(add_headers or {})
        self._remove = list(remove_headers or [])
        self._replace = dict(replace_headers or {})

    def add_header(self, name: str, value: str) -> "ResponseHeaderRewriter":
        self._add[name] = value
        return self

    def remove_header(self, name: str) -> "ResponseHeaderRewriter":
        self._remove.append(name)
        return self

    def replace_header(self, name: str, value: str) -> "ResponseHeaderRewriter":
        self._replace[name] = value
        return self

    def rewrite(self, response: Response, request: Request) -> Response:
        try:
            modified = response.copy()
            for name in self._remove:
                modified.headers.pop(name, None)
            for name, value in self._replace.items():
                if name in modified.headers:
                    modified.headers[name] = value
            for name, value in self._add.items():
                modified.headers[name] = value
            return modified
        except Exception as e:
            raise RewriterError(f"Response header rewrite failed: {e}") from e


class RequestBodyRewriter(RequestRewriter):
    def __init__(self, transformer: Optional[Callable[[bytes], bytes]] = None) -> None:
        self._transformer = transformer

    def set_transformer(self, transformer: Callable[[bytes], bytes]) -> "RequestBodyRewriter":
        self._transformer = transformer
        return self

    def rewrite(self, request: Request) -> Request:
        if self._transformer is None:
            return request
        try:
            modified = request.copy()
            modified.body = self._transformer(request.body)
            return modified
        except Exception as e:
            raise RewriterError(f"Request body rewrite failed: {e}") from e


class ResponseBodyRewriter(ResponseRewriter):
    def __init__(self, transformer: Optional[Callable[[bytes, Request], bytes]] = None) -> None:
        self._transformer = transformer

    def set_transformer(self, transformer: Callable[[bytes, Request], bytes]) -> "ResponseBodyRewriter":
        self._transformer = transformer
        return self

    def rewrite(self, response: Response, request: Request) -> Response:
        if self._transformer is None:
            return response
        try:
            modified = response.copy()
            modified.body = self._transformer(response.body, request)
            return modified
        except Exception as e:
            raise RewriterError(f"Response body rewrite failed: {e}") from e


class StatusCodeRewriter(ResponseRewriter):
    def __init__(
        self,
        mappings: Optional[Dict[int, int]] = None,
        default: Optional[int] = None,
    ) -> None:
        self._mappings = dict(mappings or {})
        self._default = default

    def add_mapping(self, from_code: int, to_code: int) -> "StatusCodeRewriter":
        self._mappings[from_code] = to_code
        return self

    def set_default(self, code: int) -> "StatusCodeRewriter":
        self._default = code
        return self

    def rewrite(self, response: Response, request: Request) -> Response:
        try:
            modified = response.copy()
            if response.status_code in self._mappings:
                modified.status_code = self._mappings[response.status_code]
            elif self._default is not None:
                modified.status_code = self._default
            return modified
        except Exception as e:
            raise RewriterError(f"Status code rewrite failed: {e}") from e


class LambdaRequestRewriter(RequestRewriter):
    def __init__(self, func: Callable[[Request], Request]) -> None:
        self._func = func

    def rewrite(self, request: Request) -> Request:
        try:
            return self._func(request)
        except Exception as e:
            raise RewriterError(f"Lambda request rewrite failed: {e}") from e


class LambdaResponseRewriter(ResponseRewriter):
    def __init__(self, func: Callable[[Response, Request], Response]) -> None:
        self._func = func

    def rewrite(self, response: Response, request: Request) -> Response:
        try:
            return self._func(response, request)
        except Exception as e:
            raise RewriterError(f"Lambda response rewrite failed: {e}") from e


class RewriterChain:
    def __init__(self) -> None:
        self._request_rewriters: List[RequestRewriter] = []
        self._response_rewriters: List[ResponseRewriter] = []

    def register_request_rewriter(self, rewriter: RequestRewriter) -> "RewriterChain":
        self._request_rewriters.append(rewriter)
        return self

    def register_response_rewriter(self, rewriter: ResponseRewriter) -> "RewriterChain":
        self._response_rewriters.append(rewriter)
        return self

    def rewrite_request(self, request: Request) -> Request:
        current = request
        for rewriter in self._request_rewriters:
            current = rewriter.rewrite(current)
        return current

    def rewrite_response(self, response: Response, request: Request) -> Response:
        current = response
        for rewriter in self._response_rewriters:
            current = rewriter.rewrite(current, request)
        return current

    @property
    def request_rewriter_count(self) -> int:
        return len(self._request_rewriters)

    @property
    def response_rewriter_count(self) -> int:
        return len(self._response_rewriters)
