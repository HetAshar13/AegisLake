"""CLI Runner for AegisLake Streaming Producer & Chaos Simulator.

Can run in dry-run/console mode or live Kafka/Redpanda publishing mode.
Automatically adapts to any terminal width (narrow or full-screen).
"""

import argparse
import shutil
import sys
import time
from datetime import datetime

# Enforce UTF-8 on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table

from aegis_streaming.contracts import CardAuthorizationEvent, ClearinghouseSettlementEvent
from aegis_streaming.producer import PaymentStreamProducer
from aegis_streaming.chaos_engine import ChaosEngine


console = Console()


def format_amount(amount: float, currency: str) -> str:
    """Formats monetary amounts with correct symbol and decimal precision."""
    symbols = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "BHD": "BD"}
    sym = symbols.get(currency, "")
    if currency == "JPY":
        return f"{sym}{amount:,.0f}"
    return f"{sym}{amount:,.2f}"


def run_simulation(tps: int = 5, total_events: int = 50, chaos_rate: float = 0.1):
    """Runs a live console demonstration of multi-rail payments and chaos injection."""
    producer = PaymentStreamProducer(customer_pool_size=100)
    terminal_width = shutil.get_terminal_size((80, 24)).columns

    console.print(
        f"[bold green]Starting AegisLake Payment Streaming Simulator[/bold green] (TPS: {tps}, Events: {total_events})"
    )
    console.print(f"[dim]Terminal width detected: {terminal_width} cols. Streaming live transactions...[/dim]\n")

    is_narrow = terminal_width < 90

    if not is_narrow:
        table = Table(title="Live Multi-Rail Payment Stream & Chaos Interceptor", expand=True)
        table.add_column("Auth ID", style="cyan", no_wrap=True)
        table.add_column("Rail", style="magenta")
        table.add_column("Customer", style="blue")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Curr", style="yellow")
        table.add_column("Status", style="white")
        table.add_column("Chaos Anomaly", style="bold")

    interval = 1.0 / tps

    for i in range(total_events):
        auth, settlement = producer.generate_pair(settlement_delay_sec=1)
        chaos_tag = "CLEAN"

        # Apply chaos probabilistically
        if i >= 3 and (i % max(1, int(1 / chaos_rate if chaos_rate > 0 else 999))) == 0:
            anomaly_type = i % 3
            if anomaly_type == 0:
                corrupted = ChaosEngine.inject_jpy_decimal_anomaly(auth)
                chaos_tag = corrupted["_chaos_tag"]
            elif anomaly_type == 1:
                corrupted = ChaosEngine.inject_negative_amount(auth)
                chaos_tag = corrupted["_chaos_tag"]
            else:
                corrupted = ChaosEngine.inject_settlement_break(auth)
                chaos_tag = corrupted["_chaos_tag"]

        amount_str = format_amount(auth.amount_base, auth.currency)
        tag_str = f"[red bold]{chaos_tag}[/red bold]" if chaos_tag != "CLEAN" else "[green]NORMAL[/green]"

        if is_narrow:
            # High-density, narrow-terminal live log
            time_str = datetime.now().strftime("%H:%M:%S")
            console.print(
                f"[dim]{time_str}[/dim] [cyan]{auth.authorization_id[:10]}..[/cyan] | "
                f"[magenta]{auth.payment_rail.value[:4]}[/magenta] | "
                f"[green bold]{amount_str:>10}[/green bold] [yellow]{auth.currency}[/yellow] | "
                f"{tag_str}"
            )
        else:
            table.add_row(
                auth.authorization_id[:14] + "...",
                auth.payment_rail.value,
                auth.customer_id[:10],
                amount_str,
                auth.currency,
                settlement.settlement_status.value,
                tag_str,
            )

        time.sleep(interval)

    if not is_narrow:
        console.print(table)

    console.print(
        f"\n[bold cyan][DONE] Simulation completed successfully! Total events generated: {total_events}[/bold cyan]"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AegisLake Payment Stream Generator")
    parser.add_argument("--tps", type=int, default=10, help="Transactions per second")
    parser.add_argument("--events", type=int, default=20, help="Total events to stream")
    parser.add_argument("--chaos", type=float, default=0.2, help="Chaos injection probability (0.0 to 1.0)")
    args = parser.parse_args()

    run_simulation(tps=args.tps, total_events=args.events, chaos_rate=args.chaos)
