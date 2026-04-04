from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table

from loophole.chatbot.agents.drafter import Drafter
from loophole.chatbot.agents.jailbreak import JailbreakFinder
from loophole.chatbot.agents.judge import Judge
from loophole.chatbot.agents.refusal import RefusalFinder
from loophole.chatbot.models import AttackType, CaseStatus, ChatbotConfig, ChatbotSession, SystemPrompt
from loophole.chatbot.session import ChatbotSessionManager
from loophole.llm import LLMClient

app = typer.Typer(name="loophole-chatbot", add_completion=False)
console = Console()


def _load_config() -> dict:
    config_path = Path("config.yaml")
    if config_path.exists():
        return yaml.safe_load(config_path.read_text())
    return {
        "model": {"default": "claude-sonnet-4-20250514", "max_tokens": 4096},
        "temperatures": {
            "legislator": 0.4,
            "loophole_finder": 0.9,
            "overreach_finder": 0.9,
            "judge": 0.3,
        },
        "loop": {"max_rounds": 10, "cases_per_agent": 3},
        "session_dir": "sessions",
    }


def _build_agents(config: dict) -> dict:
    model = config["model"]["default"]
    max_tokens = config["model"]["max_tokens"]
    temps = config["temperatures"]
    cases_per = config["loop"]["cases_per_agent"]

    llm = LLMClient(model=model, max_tokens=max_tokens)

    return {
        "drafter": Drafter(llm, temperature=temps["legislator"]),
        "jailbreak": JailbreakFinder(llm, temperature=temps["loophole_finder"], cases_per_agent=cases_per),
        "refusal": RefusalFinder(llm, temperature=temps["overreach_finder"], cases_per_agent=cases_per),
        "judge": Judge(llm, temperature=temps["judge"]),
    }


def _display_prompt(prompt: SystemPrompt) -> None:
    console.print()
    console.print(
        Panel(
            prompt.text,
            title=f"[bold]System Prompt v{prompt.version}[/bold]",
            border_style="blue",
            padding=(1, 2),
        )
    )
    if prompt.changelog:
        console.print(f"[dim]Changelog: {prompt.changelog}[/dim]")
    console.print()


def _display_case(case_obj) -> None:
    if case_obj.attack_type == AttackType.JAILBREAK:
        color = "red"
        label = "JAILBREAK"
        sublabel = "Bot responded when it shouldn't have"
    else:
        color = "yellow"
        label = "FALSE REFUSAL"
        sublabel = "Bot refused when it shouldn't have"

    console.print()
    console.print(
        Panel(
            f"[bold]User message:[/bold]\n{case_obj.attack_prompt}\n\n"
            f"[bold]Bot response:[/bold]\n{case_obj.bot_response}\n\n"
            f"[bold]Problem:[/bold]\n{case_obj.evaluation}",
            title=f"[{color}]Case #{case_obj.id} — {label}[/{color}]",
            subtitle=f"[{color}]{sublabel}[/{color}]",
            border_style=color,
            padding=(1, 2),
        )
    )


def _get_multiline_input(prompt_text: str) -> str:
    console.print(f"\n[bold]{prompt_text}[/bold]")
    console.print("[dim](Enter a blank line when finished)[/dim]")
    lines = []
    while True:
        line = Prompt.ask("", default="")
        if line == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _run_adversarial_loop(state: ChatbotSession, agents: dict, session_mgr: ChatbotSessionManager, config: dict):
    max_rounds = config["loop"]["max_rounds"]
    drafter: Drafter = agents["drafter"]
    jailbreak_finder: JailbreakFinder = agents["jailbreak"]
    refusal_finder: RefusalFinder = agents["refusal"]
    judge: Judge = agents["judge"]

    consecutive_empty = 0  # Track rounds with no confirmed failures

    while state.current_round < max_rounds:
        state.current_round += 1
        console.print(Rule(f"[bold] Round {state.current_round} [/bold]", style="cyan"))

        # Phase 1: Adversarial attacks (craft, run, evaluate)
        console.print("\n[bold]Running jailbreak attacks (single + multi-turn)...[/bold]", end="")
        jailbreaks, jailbreak_attempts = jailbreak_finder.find(state)
        state.attempts.extend(jailbreak_attempts)
        console.print(
            f" {len(jailbreak_attempts)} attempted, "
            f"[red]{len(jailbreaks)} confirmed failures[/red]"
        )

        console.print("[bold]Running refusal tests...[/bold]", end="")
        refusals, refusal_attempts = refusal_finder.find(state)
        state.attempts.extend(refusal_attempts)
        console.print(
            f" {len(refusal_attempts)} attempted, "
            f"[yellow]{len(refusals)} confirmed failures[/yellow]"
        )

        session_mgr.save(state)  # Save attempts even if no failures

        all_cases = jailbreaks + refusals

        if not all_cases:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                console.print(
                    f"\n[green bold]No failures found for {consecutive_empty} consecutive rounds! "
                    "The system prompt appears robust.[/green bold]"
                )
                if not Confirm.ask("Keep testing anyway?", default=False):
                    break
            else:
                console.print(
                    "\n[green]No failures this round. Running another round to confirm...[/green]"
                )
            continue

        consecutive_empty = 0

        # Phase 2: Judge each case
        round_auto = 0
        round_escalated = 0

        for case_obj in all_cases:
            state.cases.append(case_obj)
            _display_case(case_obj)

            console.print("  [dim]Judge evaluating...[/dim]", end="")
            result = judge.evaluate(state, case_obj)

            if result.resolvable:
                case_obj.resolution = result.resolution_summary or result.reasoning
                case_obj.status = CaseStatus.AUTO_RESOLVED
                case_obj.resolved_by = "judge"

                revised = drafter.revise(state, case_obj)

                if state.resolved_cases:
                    console.print(" [dim]validating...[/dim]", end="")
                    validation = judge.validate(state, revised.text)
                    if validation.passes:
                        state.current_prompt = revised
                        state.prompt_history.append(revised)
                        console.print(f" [green]Resolved -> Prompt v{revised.version}[/green]")
                        round_auto += 1
                    else:
                        case_obj.status = CaseStatus.ESCALATED
                        case_obj.resolution = None
                        case_obj.resolved_by = None
                        console.print(" [red]Validation failed — escalating[/red]")
                        _escalate(state, case_obj, validation.details, drafter)
                        round_escalated += 1
                else:
                    state.current_prompt = revised
                    state.prompt_history.append(revised)
                    console.print(f" [green]Resolved -> Prompt v{revised.version}[/green]")
                    round_auto += 1
            else:
                console.print(" [red bold]Cannot resolve — escalating to you[/red bold]")
                _escalate(state, case_obj, result.conflict_explanation or result.reasoning, drafter)
                round_escalated += 1

            session_mgr.save(state)

        _display_round_summary(state, len(all_cases), round_auto, round_escalated)

        console.print()
        action = Prompt.ask(
            "[bold]Next?[/bold]",
            choices=["continue", "view prompt", "stop"],
            default="continue",
        )
        if action == "view prompt":
            _display_prompt(state.current_prompt)
            if not Confirm.ask("Continue to next round?", default=True):
                break
        elif action == "stop":
            break

    console.print(Rule("[bold green] Session Complete [/bold green]", style="green"))
    _display_prompt(state.current_prompt)
    console.print(
        f"[bold]Final stats:[/bold] {len(state.cases)} cases over "
        f"{state.current_round} rounds, prompt at v{state.current_prompt.version}"
    )
    console.print(
        f"[dim]Session saved to: sessions/{state.session_id}/[/dim]"
    )

    # Generate HTML report
    from loophole.chatbot.visualize import generate_html
    report_path = generate_html(state)
    console.print(f"[bold blue]HTML report:[/bold blue] {report_path}")


def _escalate(state, case_obj, conflict_text, drafter):
    console.print(
        Panel(
            f"[bold]The judge could not resolve this without breaking prior fixes.[/bold]\n\n"
            f"{conflict_text or 'No additional conflict details.'}",
            title="[red bold]Escalation[/red bold]",
            border_style="red",
            padding=(1, 2),
        )
    )

    decision = _get_multiline_input(
        "How should the system prompt handle this? Your decision becomes a new constraint:"
    )

    case_obj.status = CaseStatus.USER_RESOLVED
    case_obj.resolution = decision
    case_obj.resolved_by = "user"
    state.user_clarifications.append(
        f"[Case #{case_obj.id}] {decision}"
    )

    console.print("  [dim]Updating system prompt...[/dim]")
    revised = drafter.revise(state, case_obj)
    state.current_prompt = revised
    state.prompt_history.append(revised)
    console.print(f"  [green]Prompt updated -> v{revised.version}[/green]")


def _display_round_summary(state, total, auto, escalated):
    console.print()
    table = Table(title=f"Round {state.current_round} Summary", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Failures found", str(total))
    table.add_row("Auto-resolved", f"[green]{auto}[/green]")
    table.add_row("Escalated to user", f"[red]{escalated}[/red]")
    table.add_row("System prompt version", f"v{state.current_prompt.version}")
    table.add_row("Total resolved cases", str(len(state.resolved_cases)))
    console.print(table)


@app.command()
def new(
    company: str = typer.Option(None, help="Company name"),
    description: str = typer.Option(None, "--desc", help="What the company does"),
    chatbot_config_file: str = typer.Option(None, "--chatbot-config", "-c", help="Path to a YAML chatbot config file"),
):
    """Start a new chatbot system prompt session."""
    console.print(
        Panel(
            "[bold]Loophole — Chatbot Mode[/bold]\n"
            "Stress-test your chatbot's system prompt",
            border_style="bright_blue",
            padding=(1, 2),
        )
    )

    config = _load_config()
    agents = _build_agents(config)

    if chatbot_config_file:
        # Load from YAML config file
        chatbot_data = yaml.safe_load(Path(chatbot_config_file).read_text())
        chatbot_config = ChatbotConfig(
            company_name=chatbot_data["company_name"],
            company_description=chatbot_data["company_description"],
            chatbot_purpose=chatbot_data["chatbot_purpose"],
            should_talk_about=chatbot_data["should_talk_about"],
            should_not_talk_about=chatbot_data["should_not_talk_about"],
            tone=chatbot_data.get("tone", "Professional and helpful"),
        )
        company = chatbot_config.company_name
        console.print(f"[dim]Loaded chatbot config from {chatbot_config_file}[/dim]")
        console.print(f"[bold]Company:[/bold] {chatbot_config.company_name}")
        console.print(f"[bold]Purpose:[/bold] {chatbot_config.chatbot_purpose}")
    else:
        if not company:
            company = Prompt.ask("\n[bold]Company name[/bold]")
        if not description:
            description = Prompt.ask("[bold]What does the company do?[/bold]")

        purpose = Prompt.ask("[bold]What should the chatbot help with?[/bold]")

        should_talk = _get_multiline_input("What topics SHOULD it talk about?")
        should_not_talk = _get_multiline_input("What topics should it NOT talk about?")
        tone = Prompt.ask("[bold]Tone/personality[/bold]", default="Professional and helpful")

        chatbot_config = ChatbotConfig(
            company_name=company,
            company_description=description,
            chatbot_purpose=purpose,
            should_talk_about=should_talk,
            should_not_talk_about=should_not_talk,
            tone=tone,
        )

    session_id = f"chatbot_{company.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_mgr = ChatbotSessionManager(config["session_dir"])

    # Generate initial system prompt
    console.print("\n[bold]Generating initial system prompt...[/bold]")
    drafter: Drafter = agents["drafter"]

    placeholder = ChatbotSession(
        session_id=session_id,
        config=chatbot_config,
        current_prompt=SystemPrompt(version=0, text=""),
    )
    initial_prompt = drafter.draft_initial(placeholder)

    state = session_mgr.create_session(session_id, chatbot_config, initial_prompt)
    _display_prompt(state.current_prompt)

    if Confirm.ask("Begin adversarial testing?", default=True):
        _run_adversarial_loop(state, agents, session_mgr, config)


@app.command()
def resume(
    session_id: str = typer.Argument(None, help="Session ID to resume"),
):
    """Resume an existing chatbot session."""
    config = _load_config()
    session_mgr = ChatbotSessionManager(config["session_dir"])

    if not session_id:
        sessions = session_mgr.list_sessions()
        if not sessions:
            console.print("[red]No chatbot sessions found.[/red]")
            raise typer.Exit()

        table = Table(title="Available Chatbot Sessions")
        table.add_column("#", style="dim")
        table.add_column("Session ID")
        table.add_column("Company")
        table.add_column("Round")
        table.add_column("Cases")
        table.add_column("Prompt Version")
        for i, s in enumerate(sessions, 1):
            table.add_row(
                str(i), s["id"], s["company"],
                str(s["round"]), str(s["cases"]), f"v{s['prompt_version']}"
            )
        console.print(table)

        choice = Prompt.ask("Select session number")
        session_id = sessions[int(choice) - 1]["id"]

    state = session_mgr.load(session_id)
    agents = _build_agents(config)

    console.print(f"\n[bold]Resuming session:[/bold] {session_id}")
    console.print(
        f"Company: {state.config.company_name} | Round: {state.current_round} | "
        f"Prompt: v{state.current_prompt.version}"
    )
    _display_prompt(state.current_prompt)

    _run_adversarial_loop(state, agents, session_mgr, config)


@app.command(name="list")
def list_sessions():
    """List all chatbot sessions."""
    config = _load_config()
    session_mgr = ChatbotSessionManager(config["session_dir"])
    sessions = session_mgr.list_sessions()

    if not sessions:
        console.print("[dim]No chatbot sessions found.[/dim]")
        return

    table = Table(title="Chatbot Sessions")
    table.add_column("Session ID")
    table.add_column("Company")
    table.add_column("Round")
    table.add_column("Cases")
    table.add_column("Prompt Version")
    for s in sessions:
        table.add_row(
            s["id"], s["company"],
            str(s["round"]), str(s["cases"]), f"v{s['prompt_version']}"
        )
    console.print(table)


@app.command()
def visualize(
    session_id: str = typer.Argument(None, help="Session ID to visualize"),
    output: str = typer.Option(None, "--output", "-o", help="Output HTML file path"),
):
    """Generate an HTML visualization of a chatbot session."""
    config = _load_config()
    session_mgr = ChatbotSessionManager(config["session_dir"])

    if not session_id:
        sessions = session_mgr.list_sessions()
        if not sessions:
            console.print("[red]No chatbot sessions found.[/red]")
            raise typer.Exit()

        table = Table(title="Available Chatbot Sessions")
        table.add_column("#", style="dim")
        table.add_column("Session ID")
        table.add_column("Company")
        table.add_column("Cases")
        for i, s in enumerate(sessions, 1):
            table.add_row(str(i), s["id"], s["company"], str(s["cases"]))
        console.print(table)

        choice = Prompt.ask("Select session number")
        session_id = sessions[int(choice) - 1]["id"]

    state = session_mgr.load(session_id)

    from loophole.chatbot.visualize import generate_html
    report_path = generate_html(state, output_path=output)
    console.print(f"[bold green]Report generated:[/bold green] {report_path}")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Loophole Chatbot — Stress-test your chatbot's system prompt."""
    if ctx.invoked_subcommand is None:
        console.print(
            Panel(
                "[bold]Loophole — Chatbot Mode[/bold]\n"
                "Stress-test your chatbot's system prompt",
                border_style="bright_blue",
                padding=(1, 2),
            )
        )
        console.print("  1. [bold]New session[/bold]")
        console.print("  2. [bold]Resume session[/bold]")
        console.print("  3. [bold]List sessions[/bold]")
        console.print("  4. [bold]Exit[/bold]")
        console.print()

        choice = Prompt.ask("Select", choices=["1", "2", "3", "4"], default="1")

        if choice == "1":
            ctx.invoke(new, company=None, description=None)
        elif choice == "2":
            ctx.invoke(resume, session_id=None)
        elif choice == "3":
            ctx.invoke(list_sessions)
        else:
            raise typer.Exit()


if __name__ == "__main__":
    app()
