from __future__ import annotations

import argparse
import asyncio
import json
import sys

from main import DEFAULT_ROUNDS, format_result
from secure_runtime import SecureHyperOrchestrator


async def run_once(prompt: str, rounds: int, raw_json: bool) -> int:
    async with SecureHyperOrchestrator(rounds=rounds) as runtime:
        result = await runtime.ask(prompt)
    if raw_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_result(result, raw_json=False))
        memory = result.get("secure_memory", {})
        print("\nsecure-memory:")
        print(json.dumps(memory, indent=2, ensure_ascii=False))
    return 0


async def interactive(rounds: int, raw_json: bool) -> int:
    print("DSG Secure HyperCommunication / PCOSM")
    print("Commands: /quit, /status\n")
    async with SecureHyperOrchestrator(rounds=rounds) as runtime:
        while True:
            try:
                prompt = await asyncio.to_thread(input, "secure-hyper> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            prompt = prompt.strip()
            if not prompt:
                continue
            if prompt in {"/quit", "/exit", "quit", "exit"}:
                break
            if prompt == "/status":
                print(json.dumps(runtime.memory.status().__dict__ if hasattr(runtime.memory.status(), "__dict__") else {
                    "persistent_master_key": runtime.memory.status().persistent_master_key,
                    "vector_backend": runtime.memory.status().vector_backend,
                    "ckks_enabled": runtime.memory.status().ckks_enabled,
                    "ckks_library_available": runtime.memory.status().ckks_library_available,
                    "blind_dimensions": runtime.memory.status().blind_dimensions,
                    "warnings": runtime.memory.status().warnings,
                }, indent=2))
                continue
            result = await runtime.ask(prompt)
            print(json.dumps(result, indent=2, ensure_ascii=False) if raw_json else format_result(result, raw_json=False))
            print()
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DSG Secure HyperCommunication / PCOSM")
    parser.add_argument("prompt", nargs="*", help="one-shot task; omit for interactive mode")
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    prompt = " ".join(args.prompt).strip()
    try:
        return asyncio.run(run_once(prompt, args.rounds, args.json) if prompt else interactive(args.rounds, args.json))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
