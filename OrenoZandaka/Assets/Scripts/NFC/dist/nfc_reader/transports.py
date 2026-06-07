from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class TransportConfig:
    protocol: str
    host: str
    port: int
    timeout_seconds: float


class EventTransport:
    def send(self, event: dict) -> None:
        raise NotImplementedError


class TcpEventTransport(EventTransport):
    def __init__(self, host: str, port: int, timeout_seconds: float) -> None:
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds

    def send(self, event: dict) -> None:
        payload = (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")
        with socket.create_connection((self._host, self._port), timeout=self._timeout_seconds) as sock:
            sock.sendall(payload)


class UdpEventTransport(EventTransport):
    def __init__(self, host: str, port: int, timeout_seconds: float) -> None:
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds

    def send(self, event: dict) -> None:
        payload = json.dumps(event, ensure_ascii=False).encode("utf-8")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(self._timeout_seconds)
            sock.sendto(payload, (self._host, self._port))


def load_transport_config() -> TransportConfig:
    protocol = os.getenv("NFC_TRANSPORT_PROTOCOL", "tcp").strip().lower()
    host = os.getenv("NFC_TRANSPORT_HOST", os.getenv("TCP_INGEST_HOST", "127.0.0.1"))
    port = int(os.getenv("NFC_TRANSPORT_PORT", os.getenv("TCP_INGEST_PORT", "9000")))
    timeout_seconds = float(os.getenv("NFC_TRANSPORT_TIMEOUT_SECONDS", "5"))
    return TransportConfig(
        protocol=protocol,
        host=host,
        port=port,
        timeout_seconds=timeout_seconds,
    )


def create_transport(config: TransportConfig | None = None) -> EventTransport:
    current = config or load_transport_config()
    if current.protocol == "tcp":
        return TcpEventTransport(current.host, current.port, current.timeout_seconds)
    if current.protocol == "udp":
        return UdpEventTransport(current.host, current.port, current.timeout_seconds)
    raise ValueError(f"Unsupported NFC transport protocol: {current.protocol}")
