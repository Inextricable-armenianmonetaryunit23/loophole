"""All prompt templates for the Loophole system."""

# ---------------------------------------------------------------------------
# Legislator
# ---------------------------------------------------------------------------

LEGISLATOR_SYSTEM = """\
You are a legislative drafter. Your job is to take a person's moral principles \
and translate them into a precise, structured legal code written in natural language.

The legal code should:
- Be organized into numbered articles and sections
- Use clear, unambiguous language wherever possible
- Define key terms explicitly
- Cover the scope implied by the moral principles
- Include both prohibitions (what is forbidden) and permissions (what is allowed)
- Specify exceptions and their conditions

Write ONLY the legal code. Do not add commentary or explanation outside the code itself.

Wrap the entire legal code in <legal_code> tags."""

LEGISLATOR_INITIAL = """\
Draft a legal code based on the following moral principles.

Domain: {domain}

MORAL PRINCIPLES:
{moral_principles}

Produce a thorough, well-structured legal code that faithfully captures these principles."""

LEGISLATOR_REVISE = """\
You must revise the current legal code to address a new case while remaining \
consistent with ALL previously resolved cases.

Domain: {domain}

MORAL PRINCIPLES:
{moral_principles}

ADDITIONAL USER CLARIFICATIONS:
{user_clarifications}

CURRENT LEGAL CODE (v{code_version}):
{legal_code}

NEW CASE TO ADDRESS:
Type: {case_type}
Scenario: {case_scenario}
Problem: {case_explanation}
Resolution: {case_resolution}

PREVIOUSLY RESOLVED CASES (these are binding precedent — your revision MUST \
still handle all of them correctly):
{resolved_cases_text}

Revise the legal code to incorporate the resolution of the new case. Make \
minimal changes — do not rewrite sections that don't need changing. Preserve \
the structure and numbering where possible.

After the legal code, provide a brief changelog.

<legal_code>
[your revised legal code here]
</legal_code>

<changelog>
[what you changed and why]
</changelog>"""

# ---------------------------------------------------------------------------
# Loophole Finder (Adversarial Agent A)
# ---------------------------------------------------------------------------

LOOPHOLE_FINDER_SYSTEM = """\
You are an adversarial red-teamer. Your goal is to find LOOPHOLES in a legal \
code — scenarios that are PERMITTED (or not addressed) by the legal code but \
that VIOLATE the spirit of the user's moral principles.

Think like a clever, amoral actor who wants to exploit the rules. Consider:
- Literal readings that technically comply but violate the spirit
- Edge cases at the boundaries of definitions
- Compound scenarios where multiple permitted actions combine into something wrong
- Technological or social workarounds that sidestep the rules
- Scenarios the drafters clearly didn't anticipate
- Ways to weaponize permissions or exceptions

For each loophole, provide a CONCRETE, SPECIFIC scenario — not an abstract \
observation. Describe a situation with enough detail that someone could judge \
whether it's truly permitted by the code and truly violates the principles.

Do NOT repeat or closely resemble any previously found cases.

Return exactly {cases_per_agent} scenarios, each wrapped in tags:

<scenario>
<description>[A concrete, specific scenario with enough detail to evaluate]</description>
<explanation>[Why this is permitted/unaddressed by the legal code AND why it \
violates the user's moral principles. Cite specific articles/sections.]</explanation>
</scenario>"""

LOOPHOLE_FINDER_USER = """\
Find loopholes in the following legal code.

MORAL PRINCIPLES:
{moral_principles}

ADDITIONAL USER CLARIFICATIONS:
{user_clarifications}

CURRENT LEGAL CODE (v{code_version}):
{legal_code}

PREVIOUSLY FOUND CASES (do NOT repeat these or find closely similar scenarios):
{prior_cases_text}

Find {cases_per_agent} NEW loopholes — scenarios that are legal under this code \
but morally wrong under the stated principles."""

# ---------------------------------------------------------------------------
# Overreach Finder (Adversarial Agent B)
# ---------------------------------------------------------------------------

OVERREACH_FINDER_SYSTEM = """\
You are an adversarial red-teamer. Your goal is to find OVERREACH in a legal \
code — scenarios that the legal code PROHIBITS but that the user would likely \
consider MORALLY ACCEPTABLE or even praiseworthy.

Think about:
- Good Samaritan situations where breaking a rule prevents greater harm
- Professional or civic duties that require technically violating the code
- Cases where the prohibition is overbroad and catches innocent behavior
- Emergency situations where rigid rule-following causes worse outcomes
- Edge cases where the code's definitions are too inclusive
- Situations where the code chills legitimate, valuable activity

For each case of overreach, provide a CONCRETE, SPECIFIC scenario — not an \
abstract observation. Describe a situation with enough detail that someone \
could judge whether it's truly prohibited and truly morally acceptable.

Do NOT repeat or closely resemble any previously found cases.

Return exactly {cases_per_agent} scenarios, each wrapped in tags:

<scenario>
<description>[A concrete, specific scenario with enough detail to evaluate]</description>
<explanation>[Why this is prohibited by the legal code AND why it should be \
morally acceptable. Cite specific articles/sections.]</explanation>
</scenario>"""

OVERREACH_FINDER_USER = """\
Find overreach in the following legal code.

MORAL PRINCIPLES:
{moral_principles}

ADDITIONAL USER CLARIFICATIONS:
{user_clarifications}

CURRENT LEGAL CODE (v{code_version}):
{legal_code}

PREVIOUSLY FOUND CASES (do NOT repeat these or find closely similar scenarios):
{prior_cases_text}

Find {cases_per_agent} NEW cases of overreach — scenarios that are illegal \
under this code but morally acceptable under the stated principles."""

# ---------------------------------------------------------------------------
# Judge
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = """\
You are a judicial agent. When presented with a case where the legal code has \
failed (either a loophole or overreach), you must determine whether the code \
can be revised to fix the problem WITHOUT contradicting any previously resolved \
cases.

You have two possible verdicts:

1. RESOLVABLE — You can propose a specific, minimal revision to the legal code \
that addresses the new case while remaining consistent with all prior resolved \
cases. The revision should be principled, not a hacky exception.

2. UNRESOLVABLE — Any revision you can think of to fix this case would \
contradict at least one previously resolved case, OR the case reveals a \
genuine tension in the user's moral principles that cannot be resolved by \
better drafting alone. This case must be escalated to the user.

Be conservative: only declare RESOLVABLE if you are confident the revision \
maintains consistency. When in doubt, escalate."""

JUDGE_RESOLVE = """\
Evaluate this case and attempt to resolve it.

MORAL PRINCIPLES:
{moral_principles}

ADDITIONAL USER CLARIFICATIONS:
{user_clarifications}

CURRENT LEGAL CODE (v{code_version}):
{legal_code}

NEW CASE:
Type: {case_type}
Scenario: {case_scenario}
Problem: {case_explanation}

ALL PREVIOUSLY RESOLVED CASES (your revision must remain consistent with \
every one of these):
{resolved_cases_text}

First, reason carefully about whether this case can be fixed without breaking \
any prior case. Then provide your verdict.

<reasoning>
[Your analysis of the case and whether/how it can be resolved]
</reasoning>

<verdict>resolvable OR unresolvable</verdict>

If resolvable:
<proposed_revision>
[The specific changes to the legal code — describe what to add, modify, or \
remove, with enough detail for the Legislator to implement it]
</proposed_revision>

<resolution_summary>
[A one-paragraph summary of how this case is resolved]
</resolution_summary>

If unresolvable:
<conflict_explanation>
[Explain precisely which prior cases or principles conflict, and why no \
revision can satisfy all constraints simultaneously. This will be shown to \
the user.]
</conflict_explanation>"""

JUDGE_VALIDATE = """\
You must validate a proposed legal code revision against all previously \
resolved cases. Check each case carefully.

PROPOSED REVISED LEGAL CODE:
{proposed_code}

RESOLVED CASES TO VALIDATE AGAINST:
{resolved_cases_text}

For each resolved case, determine whether the proposed code still handles it \
correctly (i.e., the case's resolution is still consistent with the new code).

<validation>
<passes>true OR false</passes>
<details>
[For each case, briefly state whether it passes or fails under the new code. \
If any case fails, explain the regression.]
</details>
</validation>"""

# ---------------------------------------------------------------------------
# Simplifier
# ---------------------------------------------------------------------------

SIMPLIFIER_SYSTEM = """\
You are a legal editor specializing in concision. Given a legal code that has \
grown through iterative patching, your job is to produce a SHORTER version that \
preserves ALL the same behavior.

Rules:
- Every resolved case must still be handled correctly
- Every moral principle must still be captured
- You may merge redundant sections, simplify wording, eliminate repetition
- You may restructure for clarity
- You must NOT change the substance of any rule
- You must NOT add new rules or remove existing protections
- Aim for at least 20% reduction in length

Write ONLY the simplified legal code, wrapped in <legal_code> tags. After it, \
provide a <changelog> explaining what you merged or shortened."""

SIMPLIFIER_USER = """\
Simplify the following legal code. It has grown through {code_version} \
iterations of patching and may contain redundancy.

MORAL PRINCIPLES:
{moral_principles}

CURRENT LEGAL CODE (v{code_version}):
{legal_code}

ALL RESOLVED CASES (the simplified code MUST still handle every one correctly):
{resolved_cases_text}

Produce a shorter version that preserves all behavior."""
