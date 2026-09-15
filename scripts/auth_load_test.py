"""对已启动的认证服务执行固定到达率 HTTP 压测。"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx


@dataclass(frozen=True)
class RequestResult:
    latency_ms: float
    successful: bool
    status_code: int | None
    error: str | None = None


@dataclass(frozen=True)
class Thresholds:
    max_error_rate: float
    max_p95_ms: float
    max_p99_ms: float


def percentile(values: list[float], percentile_value: float) -> float:
    """使用 nearest-rank 计算百分位，结果可与常见压测工具对照。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile_value / 100 * len(ordered)))
    return ordered[rank - 1]


def synthetic_client(index: int) -> tuple[str, str, str]:
    """生成唯一的 RFC1918 IP、locally administered MAC 和接入设备 MAC。"""
    value = index + 1
    second = (value // (254 * 254)) % 16 + 16
    third = (value // 254) % 254 + 1
    fourth = value % 254 + 1
    client_ip = f"10.{second}.{third}.{fourth}"
    client_mac = "02:%02X:%02X:%02X:%02X:%02X" % (
        (value >> 32) & 0xFF,
        (value >> 24) & 0xFF,
        (value >> 16) & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF,
    )
    device_mac = "06:%02X:%02X:%02X:%02X:%02X" % (
        (value >> 32) & 0xFF,
        (value >> 24) & 0xFF,
        (value >> 16) & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF,
    )
    return client_ip, client_mac, device_mac


def boarding_pass_request(index: int, args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    client_ip, client_mac, device_mac = synthetic_client(index)
    return (
        "/api/v1/portal/boarding-pass/verify",
        {
            "json": {
                "flightDate": args.flight_date,
                "flightNo": args.flight_no,
                "seatNo": args.seat_no,
                "documentLast4": args.document_last4,
                "clientIp": client_ip,
                "clientMac": client_mac,
                "ssid": args.ssid,
                "deviceMac": device_mac,
            }
        },
    )


def passport_request(index: int, args: argparse.Namespace, image: bytes) -> tuple[str, dict[str, Any]]:
    client_ip, client_mac, device_mac = synthetic_client(index)
    return (
        "/api/v1/portal/passport/verify",
        {
            "content": image,
            "headers": {
                "Content-Type": args.passport_content_type,
                "X-Client-IP": client_ip,
                "X-Client-MAC": client_mac,
                "X-SSID": args.ssid,
                "X-Device-MAC": device_mac,
            },
        },
    )


def build_request(
    index: int,
    args: argparse.Namespace,
    passport_image: bytes,
) -> tuple[str, dict[str, Any]]:
    use_passport = args.scenario == "passport" or (args.scenario == "mixed" and index % 2 == 1)
    if use_passport:
        return passport_request(index, args, passport_image)
    return boarding_pass_request(index, args)


def summarize(
    results: list[RequestResult],
    *,
    target_rps: float,
    configured_duration_seconds: float,
    actual_elapsed_seconds: float,
    scenario: str,
    concurrency: int,
    thresholds: Thresholds,
) -> tuple[dict[str, Any], list[str]]:
    latencies = [item.latency_ms for item in results]
    successful = sum(item.successful for item in results)
    failed = len(results) - successful
    error_rate = failed / len(results) if results else 1.0
    error_examples = [item.error for item in results if item.error][:10]
    status_counts: dict[str, int] = {}
    for item in results:
        status = str(item.status_code) if item.status_code is not None else "transportError"
        status_counts[status] = status_counts.get(status, 0) + 1
    report: dict[str, Any] = {
        "scenario": scenario,
        "targetRps": target_rps,
        "maxConcurrency": concurrency,
        "configuredDurationSeconds": round(configured_duration_seconds, 3),
        "actualElapsedSeconds": round(actual_elapsed_seconds, 3),
        "requests": len(results),
        "successful": successful,
        "failed": failed,
        "errorRate": round(error_rate, 6),
        "statusCounts": status_counts,
        "completedRps": round(len(results) / actual_elapsed_seconds, 3) if actual_elapsed_seconds else 0.0,
        "latencyMs": {
            "min": round(min(latencies), 3) if latencies else 0.0,
            "mean": round(statistics.fmean(latencies), 3) if latencies else 0.0,
            "p50": round(percentile(latencies, 50), 3),
            "p95": round(percentile(latencies, 95), 3),
            "p99": round(percentile(latencies, 99), 3),
            "max": round(max(latencies), 3) if latencies else 0.0,
        },
        "thresholds": asdict(thresholds),
        "errorExamples": error_examples,
    }
    violations: list[str] = []
    if not results:
        violations.append("未发出任何请求")
    if error_rate > thresholds.max_error_rate:
        violations.append(f"错误率 {error_rate:.2%} 超过阈值 {thresholds.max_error_rate:.2%}")
    if report["latencyMs"]["p95"] > thresholds.max_p95_ms:
        violations.append(f"P95 {report['latencyMs']['p95']:.3f}ms 超过阈值 {thresholds.max_p95_ms:.3f}ms")
    if report["latencyMs"]["p99"] > thresholds.max_p99_ms:
        violations.append(f"P99 {report['latencyMs']['p99']:.3f}ms 超过阈值 {thresholds.max_p99_ms:.3f}ms")
    report["passed"] = not violations
    report["violations"] = violations
    return report, violations


async def send_request(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    index: int,
    args: argparse.Namespace,
    passport_image: bytes,
) -> RequestResult:
    path, request_kwargs = build_request(index, args, passport_image)
    request_headers = dict(request_kwargs.pop("headers", {}))
    request_headers["X-Request-ID"] = uuid4().hex
    started = time.perf_counter()
    try:
        async with semaphore:
            response = await client.post(path, headers=request_headers, **request_kwargs)
        latency_ms = (time.perf_counter() - started) * 1000
        if response.status_code != 200:
            return RequestResult(latency_ms, False, response.status_code, f"HTTP {response.status_code}")
        try:
            body = response.json()
        except ValueError:
            return RequestResult(latency_ms, False, response.status_code, "响应不是 JSON")
        if not isinstance(body, dict) or not isinstance(body.get("data"), dict):
            return RequestResult(latency_ms, False, response.status_code, "响应 JSON 结构不符合接口契约")
        if body["data"].get("networkAuthorized") is not True:
            return RequestResult(latency_ms, False, response.status_code, "networkAuthorized 不为 true")
        return RequestResult(latency_ms, True, response.status_code)
    except httpx.TimeoutException:
        return RequestResult((time.perf_counter() - started) * 1000, False, None, "请求超时")
    except httpx.HTTPError as exc:
        return RequestResult((time.perf_counter() - started) * 1000, False, None, type(exc).__name__)


async def run_load(args: argparse.Namespace) -> tuple[dict[str, Any], list[str]]:
    total_requests = max(1, round(args.rps * args.duration_seconds))
    interval = 1 / args.rps
    passport_image = Path(args.passport_image).read_bytes() if args.passport_image else b"\xff\xd8\xffmock-passport"
    timeout = httpx.Timeout(args.timeout_seconds)
    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    semaphore = asyncio.Semaphore(args.concurrency)
    started = time.perf_counter()
    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/"),
        timeout=timeout,
        limits=limits,
        verify=not args.insecure,
    ) as client:
        if not args.skip_health_check:
            health = await client.get("/health/ready")
            health.raise_for_status()

        tasks: list[asyncio.Task[RequestResult]] = []
        schedule_started = time.perf_counter()
        for index in range(total_requests):
            due_at = schedule_started + index * interval
            delay = due_at - time.perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
            tasks.append(asyncio.create_task(send_request(client, semaphore, index, args, passport_image)))
        results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - started
    thresholds = Thresholds(args.max_error_rate, args.max_p95_ms, args.max_p99_ms)
    return summarize(
        results,
        target_rps=args.rps,
        configured_duration_seconds=args.duration_seconds,
        actual_elapsed_seconds=elapsed,
        scenario=args.scenario,
        concurrency=args.concurrency,
        thresholds=thresholds,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="深圳机场 WiFi Portal 认证固定到达率压测工具")
    parser.add_argument("--base-url", default="http://127.0.0.1:80", help="Nginx 入口地址")
    parser.add_argument("--scenario", choices=("boarding-pass", "passport", "mixed"), default="mixed")
    parser.add_argument("--rps", type=float, default=50.0, help="每秒发起请求数")
    parser.add_argument("--duration-seconds", type=float, default=60.0)
    parser.add_argument("--concurrency", type=int, default=50, help="最大在途请求数")
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--max-p95-ms", type=float, default=1000.0)
    parser.add_argument("--max-p99-ms", type=float, default=2000.0)
    parser.add_argument("--flight-date", default="2026-09-10")
    parser.add_argument("--flight-no", default="CA1234")
    parser.add_argument("--seat-no", default="16A")
    parser.add_argument("--document-last4", default="5678")
    parser.add_argument("--ssid", default="Airport-Free-WiFi")
    parser.add_argument("--passport-image", help="真实 OCR 场景使用的脱敏测试图片")
    parser.add_argument("--passport-content-type", choices=("image/jpeg", "image/png"), default="image/jpeg")
    parser.add_argument("--insecure", action="store_true", help="仅联调时跳过 HTTPS 证书校验")
    parser.add_argument("--skip-health-check", action="store_true")
    parser.add_argument("--report", type=Path, help="另存 JSON 报告；建议写入被忽略的 .tmp 目录")
    args = parser.parse_args(argv)
    if args.rps <= 0 or args.duration_seconds <= 0 or args.concurrency <= 0 or args.timeout_seconds <= 0:
        parser.error("rps、duration-seconds、concurrency 和 timeout-seconds 必须大于 0")
    if not 0 <= args.max_error_rate <= 1:
        parser.error("max-error-rate 必须在 0 到 1 之间")
    if args.max_p95_ms <= 0 or args.max_p99_ms <= 0:
        parser.error("延迟阈值必须大于 0")
    try:
        date.fromisoformat(args.flight_date)
    except ValueError:
        parser.error("flight-date 必须是 YYYY-MM-DD")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report, violations = asyncio.run(run_load(args))
    except (httpx.HTTPError, OSError) as exc:
        print(f"压测启动失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
