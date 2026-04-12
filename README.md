# Loophole

**Adversarial moral-legal code system** — an AI tool that stress-tests ethical principles, system prompts, and legal texts by trying to break them.

## The Idea

Real legal systems evolve slowly. A law gets written, someone finds a loophole, a court patches it, someone finds another loophole. This process takes decades. Loophole compresses it into minutes.

You state your moral principles in plain language. An AI legislator drafts a formal legal code from them. Then two adversarial agents attack it:

- **The Loophole Finder** searches for scenarios that are *technically legal* under your code but *morally wrong* according to your principles. Think creative rule-lawyering, exploiting vague definitions, finding gaps the drafters didn't anticipate.

- **The Overreach Finder** searches for the opposite: scenarios your code *prohibits* that you'd actually consider *morally acceptable*. Good Samaritan situations, overbroad rules that catch innocent behavior, emergencies where rigid compliance causes worse outcomes.

When an attack lands, a **Judge agent** tries to patch the code automatically — but only if the fix doesn't break any previous ruling. Every resolved case becomes a permanent constraint, a growing test suite the code must satisfy.

If the Judge can't find a consistent fix — meaning any patch would contradict a prior decision — the case gets **escalated to you**. These escalated cases are guaranteed to be interesting: they represent genuine tensions in your own moral framework, places where your principles actually conflict with each other.

The legal code gets progressively more robust. But the real output isn't the code — it's what you discover about your own beliefs.

## How It Works

```
                    +-----------------+
                    |  Your Moral     |
                    |  Principles     |
                    +--------+--------+
                             |
                             v
                    +--------+--------+
                    |   Legislator    |
                    | (drafts legal   |
                    |  code from      |
                    |  principles)    |
                    +--------+--------+
                             |
                             v
              +--------------+--------------+
              |                             |
    +---------v----------+      +-----------v--------+
    |  Loophole Finder   |      |  Overreach Finder  |
    |  (legal but        |      |  (illegal but      |
    |   immoral)         |      |   moral)           |
    +--------+-----------+      +-----------+--------+
              |                             |
              +-------------+---------------+
                            |
                            v
                   +--------+--------+
                   |     Judge       |
                   | (auto-resolve   |
                   |  or escalate)   |
                   +--------+--------+
                            |
                +-----------+-----------+
                |                       |
        +-------v-------+      +-------v--------+
        | Auto-resolved |      |  Escalated     |
        | (code updated,|      |  to YOU        |
        |  case becomes |      |  (genuine      |
        |  precedent)   |      |   moral        |
        +---------------+      |   dilemma)     |
                               +----------------+
```

Each resolved case — whether by the Judge or by you — becomes binding precedent. The adversarial agents attack again, and the cycle repeats. Round after round, the legal code tightens, and the cases that reach you get harder and more revealing.

## Setup

Requires Python 3.12+ and an Anthropic API key. Optionally supports OpenAI and Ollama models (see Configuration).

```bash
# Clone and install
git clone <repo-url>
cd law
uv sync

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

Loophole has three modes: **Legal** (moral-legal code), **Chatbot** (system prompt stress-testing), and **Reverse** (extract moral DNA from legal texts).

### Mode 1: Legal — Moral-Legal Code

Build a formal legal code from your moral principles, then stress-test it.

```bash
# Interactive
uv run python -m loophole.main

# Or with a principles file
uv run python -m loophole.main new --domain privacy -p examples/privacy_principles.txt
```

Each round, adversarial agents find loopholes (legal but immoral) and overreach (illegal but moral). The Judge auto-resolves or escalates genuinely hard cases to you.

```bash
uv run python -m loophole.main resume     # Resume a session
uv run python -m loophole.main visualize  # Generate HTML report
uv run python -m loophole.main list       # List sessions
```

### Mode 2: Chatbot — System Prompt Stress-Testing

Provide your company info and chatbot rules. Loophole generates a system prompt, then adversarial agents try to break it by actually running attacks against the chatbot and evaluating the responses.

```bash
# Interactive
uv run python -m loophole.chatbot.main

# With a config file
uv run python -m loophole.chatbot.main new -c examples/dentist_chatbot.yaml

# With --weak for a minimal starting prompt (good for demos)
uv run python -m loophole.chatbot.main new -c examples/dentist_chatbot.yaml --weak
```

Two adversarial agents attack each round using both single-turn and multi-turn conversation strategies:
- **Jailbreak Finder**: crafts prompts that get the bot to discuss forbidden topics. Each attack is actually *run* against the chatbot, then evaluated. Includes multi-turn attacks that build rapport across 3-4 messages before pivoting.
- **Refusal Finder**: crafts legitimate customer questions the bot wrongly refuses. Also run and evaluated.

Only confirmed failures (where the bot actually misbehaved) get through to the Judge. All attempts are logged regardless of outcome. If neither adversary can break the prompt for 2 consecutive rounds, the system declares it robust.

The `--weak` flag starts with a deliberately naive one-sentence system prompt with no guardrails, so you can watch the prompt harden from nothing as each attack lands and gets patched.

```bash
uv run python -m loophole.chatbot.main resume     # Resume
uv run python -m loophole.chatbot.main visualize  # HTML report
uv run python -m loophole.chatbot.main list       # List sessions
```

The HTML report shows each failure as a chat conversation: the attack prompt, the bot's actual response, why it failed, and the git-style diff of how the system prompt was patched.

### Mode 3: Reverse — Extract Moral DNA from Legal Texts

Give it any legal document. Loophole extracts the moral principles the text implies, then two adversarial agents attack those principles:

- **Contradiction Finder**: finds scenarios where two extracted principles can't both be true
- **Gap Finder**: finds moral values the text assumes but never states

Every conflict goes directly to you. You either refine the principles or mark it as a genuine, unresolvable tension. The tensions list is the real output — a map of where the document's own values contradict each other.

```bash
# With the bundled US Constitution
uv run python -m loophole.reverse.main new \
  --name "US Constitution" \
  --text examples/us_constitution.txt

# Or any legal text
uv run python -m loophole.reverse.main new --name "My Company Policy"
```

Works with constitutions, regulations, terms of service, company policies — anywhere humans write rules, there are buried contradictions.

```bash
uv run python -m loophole.reverse.main resume     # Resume
uv run python -m loophole.reverse.main visualize  # HTML report
uv run python -m loophole.reverse.main list       # List sessions
```

The HTML report highlights genuine tensions with the scenario, which principles conflict, and your notes on why it's unresolvable.

## Configuration

Edit `config.yaml` to tune the system:

```yaml
model:
  default: "claude-sonnet-4-20250514"   # Adversaries, judge, drafter
  bot: "claude-haiku-4-5-20251001"      # The chatbot being tested (chatbot mode only)
  max_tokens: 4096
  # Optional: per-role provider overrides (mix Anthropic, OpenAI, Ollama)
  # providers:
  #   loophole_finder:
  #     provider: openai
  #     model: gpt-4o
  #   judge:
  #     provider: ollama
  #     model: llama3.1:70b

temperatures:
  legislator: 0.4          # Lower = more precise drafting
  loophole_finder: 0.9     # Higher = more creative attacks
  overreach_finder: 0.9
  judge: 0.3               # Lower = more conservative judgments

loop:
  max_rounds: 10
  cases_per_agent: 3       # How many cases each attacker finds per round

oversight: false            # --oversight: review every auto-judge decision

simplify:
  enabled: false            # --simplify: compress code/prompts after patching
  every_n_rounds: 0         # 0 = only at session end

session_dir: "sessions"
```

### Multi-Model Support

Each agent role can use a different provider. Uncomment the `providers:` block in config to mix Anthropic, OpenAI, and open-source models via Ollama. Provider is inferred from model name if not specified (`claude-*` → Anthropic, `gpt-*` → OpenAI, anything else → Ollama).

### Auto-Judge Oversight

Pass `--oversight` to see every auto-judge decision before it's applied. You can accept, reject (escalate to yourself), or modify the resolution. Off by default.

### Simplification

Pass `--simplify` to compress the legal code / system prompt / principles after iterative patching. The simplifier merges redundant rules and tightens language, then validates against all resolved cases. Use `--simplify-every N` to run every N rounds instead of only at the end.

## Writing Good Principles

The system works best when your principles are:

- **Specific enough to draft from.** "I believe in fairness" is too vague. "Companies should not sell user data without explicit, informed consent" gives the legislator something to work with.
- **Broad enough to have tensions.** If your principles only cover one narrow situation, the adversarial agents won't find interesting cases. Cover the domain from multiple angles.
- **Honest.** The system surfaces conflicts in *your* beliefs. If you state principles you don't actually hold, the escalated cases won't be meaningful.

See `examples/privacy_principles.txt` for a starting point.

## Project Structure

```
loophole/
  main.py              Legal mode — CLI and adversarial loop
  models.py            Legal data models (SessionState, Case, LegalCode)
  llm.py               Multi-provider LLM abstraction (Anthropic, OpenAI, Ollama)
  prompts.py           Legal agent prompt templates
  session.py           Legal session persistence
  visualize.py         Legal HTML report generator
  agents/
    base.py            Shared base agent class
    legislator.py      Drafts and revises legal code
    loophole_finder.py Finds legal-but-immoral scenarios
    overreach_finder.py Finds illegal-but-moral scenarios
    judge.py           Auto-resolves or escalates
    simplifier.py      Compresses legal code after patching
  chatbot/
    main.py            Chatbot mode — CLI and adversarial loop
    models.py          Chatbot data models (ChatbotSession, TestCase, etc.)
    prompts.py         Chatbot agent prompt templates
    session.py         Chatbot session persistence
    visualize.py       Chatbot HTML report generator
    agents/
      drafter.py       Writes and revises system prompts
      jailbreak.py     Crafts + runs + evaluates jailbreak attacks
      refusal.py       Crafts + runs + evaluates false refusal tests
      judge.py         Auto-resolves or escalates
      simplifier.py    Compresses system prompts after patching
  reverse/
    main.py            Reverse mode — CLI and adversarial loop
    models.py          Reverse data models (ReverseSession, ReverseFinding, etc.)
    prompts.py         Reverse agent prompt templates
    session.py         Reverse session persistence
    visualize.py       Reverse HTML report generator
    agents/
      analyst.py       Extracts and revises moral principles from legal text
      contradiction_finder.py  Finds conflicts between extracted principles
      gap_finder.py    Finds values the text implies but principles miss
      simplifier.py    Compresses principles after refinement

sessions/              One directory per session (auto-created)
examples/              Example files (principles, chatbot configs, US Constitution)
config.yaml            Model and loop configuration
```

## Why This Matters

Most attempts to formalize ethics start with the rules and hope they cover everything. Loophole starts with your intuitions and systematically finds where they break down. It's less "solve ethics" and more "discover what you actually believe by watching it fail."

The same architecture applies anywhere humans write rules for AI systems: content moderation policies, LLM system prompts, codes of conduct, safety specifications. Anywhere there's a gap between what the rules say and what the rules mean, Loophole will find it.
