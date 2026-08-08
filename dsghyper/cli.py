from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from .config import RuntimeConfig
from .runtime import APP, VERSION, HyperOrchestrator, SecureHyperOrchestrator

BANNER = r"""
╔══════════════════════════════════════════════════════════════════════╗
║ DysonSphereGamma HyperCommunication v21                            ║
║ R: challenge | G: synthesis | B: verification | Γ: coupling | Sync ║
╚══════════════════════════════════════════════════════════════════════╝
""".strip()


def format_result(result: dict, raw_json: bool = False) -> str:
    if raw_json:
        return json.dumps(result, indent=2, ensure_ascii=False)
    final = result.get("final", {})
    answer = final.get("answer", "") if isinstance(final, dict) else str(final)
    lines = [
        BANNER,
        f"trace: {result.get('trace_id')}",
        f"model: {result.get('model')}",
        f"rounds: {result.get('rounds')}",
        f"spectrum: {result.get('spectrum', {}).get('dominant')} | entropy={result.get('spectrum', {}).get('entropy')}",
        f"sync-confidence: {final.get('confidence', '?') if isinstance(final, dict) else '?'}",
        "",
        answer,
    ]
    uncertainties = final.get("uncertainties", []) if isinstance(final, dict) else []
    if uncertainties:
        lines.extend(["", "Uncertainties:", *[f"  - {item}" for item in uncertainties[:8]]])
    checks = final.get("next_checks", []) if isinstance(final, dict) else []
    if checks:
        lines.extend(["", "Next checks:", *[f"  - {item}" for item in checks[:8]]])
    ledger = result.get("ledger", {})
    lines.extend(["", f"ledger: {ledger.get('records', 0)} records | verified={ledger.get('verified')} | head={str(ledger.get('head', ''))[:16]}…"])
    if "secure_memory" in result:
        memory = result["secure_memory"]
        lines.append(f"secure-memory: {memory.get('architecture')} | retrieved={memory.get('retrieved')} | stored={memory.get('stored_record_id')}")
    return "\n".join(lines)


async def _make_runtime(secure: bool, rounds: int):
    return SecureHyperOrchestrator(rounds=rounds) if secure else HyperOrchestrator(rounds=rounds)


async def run_once(prompt: str, rounds: int, raw_json: bool, secure: bool) -> int:
    runtime = await _make_runtime(secure, rounds)
    async with runtime:
        result = await runtime.ask(prompt)
    print(format_result(result, raw_json))
    return 0


async def interactive(rounds: int, raw_json: bool, secure: bool) -> int:
    print(BANNER)
    print(f"mode: {'secure-PCESM' if secure else 'standard'}")
    print("commands: /quit, /status\n")
    runtime = await _make_runtime(secure, rounds)
    async with runtime:
        while True:
            try:
                prompt = await asyncio.to_thread(input, "secure-hyper> " if secure else "hyper> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            prompt = prompt.strip()
            if not prompt:
                continue
            if prompt in {"/quit", "/exit", "quit", "exit"}:
                break
            if prompt == "/status":
                status = {
                    "app": APP,
                    "version": VERSION,
                    "mode": "secure" if secure else "standard",
                    "runtime": asdict(runtime.runtime_config) if secure else asdict(runtime.config),
                }
                if secure:
                    status["memory"] = asdict(runtime.memory.status())
                status["runtime"]["api_key"] = "SET" if status["runtime"].get("api_key") else "UNSET"
                print(json.dumps(status, indent=2, default=str))
                continue
            result = await runtime.ask(prompt)
            print("\n" + format_result(result, raw_json) + "\n")
    return 0


def parse_args(argv: list[str], *, secure_default: bool = False) -> argparse.Namespace:
    defaults = RuntimeConfig.from_env()
    parser = argparse.ArgumentParser(description=APP)
    parser.add_argument("prompt", nargs="*", help="one-shot task; omit for interactive mode")
    parser.add_argument("--rounds", type=int, default=defaults.rounds, help="bounded worker rounds (1-8)")
    parser.add_argument("--json", action="store_true", help="emit complete machine-readable result")
    parser.add_argument("--secure", action="store_true", default=secure_default, help="enable encrypted PCESM semantic memory")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, secure_default: bool = False) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv, secure_default=secure_default)
    prompt = " ".join(args.prompt).strip()
    try:
        if prompt:
            return asyncio.run(run_once(prompt, args.rounds, args.json, args.secure))
        return asyncio.run(interactive(args.rounds, args.json, args.secure))
    except KeyboardInterrupt:
        return 130
    except RuntimeError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2


def secure_main() -> int:
    return main(secure_default=True)
