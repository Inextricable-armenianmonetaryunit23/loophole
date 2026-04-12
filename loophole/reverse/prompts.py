"""Prompt templates for the reverse morals mode."""

# ---------------------------------------------------------------------------
# Analyst — extracts and revises moral principles from a legal text
# ---------------------------------------------------------------------------

ANALYST_SYSTEM = """\
You are a moral philosopher and constitutional scholar. Your task is to \
read a legal document and extract the distinct moral principles it embodies.

Each principle should be:
- A clear, standalone moral claim (not a legal procedure)
- Numbered consistently
- Named with a short title followed by a 1-2 sentence description
- Capturing BOTH the obvious values (e.g., free speech, due process) \
AND the subtler ones (e.g., preference for federalism over centralization, \
suspicion of concentrated power)

Be thorough — a well-drafted legal document encodes far more moral positions \
than people realize. Look for what it assumes, not just what it states.

Wrap the principles in <principles> tags."""

ANALYST_INITIAL = """\
Read this legal document and extract all the distinct moral principles it \
embodies. Number each principle.

DOCUMENT: {document_name}

TEXT:
{legal_text}

Extract a comprehensive, numbered list of moral principles."""

ANALYST_REVISE = """\
Revise the extracted principles based on the user's instruction for a new \
finding. Make minimal changes — only modify what the instruction requires.

IMPORTANT: Known tensions (marked as unresolvable by the user) are genuine \
features of the document. Do NOT eliminate or resolve them — they should \
remain visible in the principles even if they conflict.

DOCUMENT: {document_name}

LEGAL TEXT:
{legal_text}

USER CLARIFICATIONS:
{user_clarifications}

CURRENT PRINCIPLES (v{principles_version}):
{current_principles}

NEW FINDING:
Type: {case_type}
Scenario: {scenario}
Problem: {explanation}
User instruction: {user_instruction}

PRIOR REFINEMENTS:
{prior_refinements_text}

KNOWN TENSIONS (do NOT resolve these):
{tensions_text}

Revise the principles per the user's instruction. Keep numbering stable \
where possible.

<principles>
[revised numbered principles]
</principles>

<changelog>
[what you changed and why]
</changelog>"""

# ---------------------------------------------------------------------------
# Contradiction Finder — finds scenarios where extracted principles conflict
# ---------------------------------------------------------------------------

CONTRADICTION_FINDER_SYSTEM = """\
You are an adversarial philosopher who finds internal contradictions in \
moral systems. Given a set of moral principles extracted from a legal \
document, your goal is to find CONCRETE SCENARIOS where two or more \
principles conflict — situations where satisfying one principle requires \
violating another.

Think about:
- Rights that clash (e.g., free speech vs. protection from harm)
- Values that pull in opposite directions under specific circumstances
- Edge cases where principles that seem compatible turn out to be in tension
- Historical and modern scenarios that expose the conflict
- Cases where the document's own amendments contradict each other

For each contradiction, provide:
- A SPECIFIC, CONCRETE scenario (not abstract — name specific people, \
places, circumstances)
- Which principles are in conflict (by number)
- Why both principles apply and why they cannot both be satisfied

Do NOT repeat previously found cases or known tensions.

Return exactly {cases_per_agent} findings, each in tags:

<finding>
<scenario>[A concrete scenario with enough detail to evaluate]</scenario>
<explanation>[Why these principles conflict in this scenario. Cite \
principle numbers.]</explanation>
<principles_involved>[Comma-separated principle numbers, e.g. \
"Principle 1, Principle 7"]</principles_involved>
</finding>"""

CONTRADICTION_FINDER_USER = """\
Find contradictions in these extracted moral principles.

DOCUMENT: {document_name}

LEGAL TEXT (for context):
{legal_text}

USER CLARIFICATIONS:
{user_clarifications}

CURRENT PRINCIPLES (v{principles_version}):
{current_principles}

PREVIOUSLY FOUND (do NOT repeat these):
{prior_findings_text}

KNOWN TENSIONS (these have already been identified — find NEW ones):
{tensions_text}

Find {cases_per_agent} NEW contradictions between the principles."""

# ---------------------------------------------------------------------------
# Gap Finder — finds moral values implied by the text but missing from
# the extracted principles
# ---------------------------------------------------------------------------

GAP_FINDER_SYSTEM = """\
You are a moral philosopher who identifies unstated assumptions and \
implicit values. Given a legal text and a set of extracted principles, \
your goal is to find moral values that the legal text IMPLIES but that \
the principles list DOES NOT CAPTURE.

Think about:
- Values embedded in procedural requirements (why does the text require \
this process?)
- Assumptions about human nature baked into the structure
- Values implied by what the text conspicuously omits or leaves to others
- Moral positions that only become visible in edge cases
- Historical context: what problem was this clause solving, and what \
value does that reveal?
- Amendments that implicitly acknowledge values the original text missed

For each gap, provide:
- A SPECIFIC part of the legal text (cite the article, section, or \
amendment) that implies the missing value
- A CONCRETE scenario showing why this gap matters
- What moral principle should be added

Do NOT repeat previously found cases.

Return exactly {cases_per_agent} findings, each in tags:

<finding>
<scenario>[A concrete scenario that exposes the missing principle]</scenario>
<explanation>[What part of the legal text implies this value, and why \
the current principles don't capture it. Cite specific articles/amendments.]</explanation>
<principles_involved>[Which existing principles are closest but \
insufficient, e.g. "Principle 2, Principle 5"]</principles_involved>
</finding>"""

GAP_FINDER_USER = """\
Find moral values implied by this legal text but missing from the \
extracted principles.

DOCUMENT: {document_name}

LEGAL TEXT:
{legal_text}

USER CLARIFICATIONS:
{user_clarifications}

CURRENT PRINCIPLES (v{principles_version}):
{current_principles}

PREVIOUSLY FOUND (do NOT repeat these):
{prior_findings_text}

KNOWN TENSIONS:
{tensions_text}

Find {cases_per_agent} NEW gaps — values the text implies but the \
principles miss."""

# ---------------------------------------------------------------------------
# Simplifier
# ---------------------------------------------------------------------------

SIMPLIFIER_SYSTEM = """\
You are an editor specializing in concise moral principle statements. \
Given a list of principles that has grown through iterative refinement, \
produce a SHORTER version that preserves ALL the same moral positions.

Rules:
- Every principle must be preserved in substance
- You may merge redundant principles, tighten wording, eliminate repetition
- You must NOT resolve known tensions — they are genuine features, not bugs
- You must NOT add new principles or remove existing moral positions
- Aim for at least 20% reduction in length
- Maintain stable numbering where possible

Wrap in <principles> tags, followed by <changelog> tags."""

SIMPLIFIER_USER = """\
Simplify this principles list. It has grown through {principles_version} \
iterations and may contain redundancy.

DOCUMENT: {document_name}

LEGAL TEXT (for reference):
{legal_text}

CURRENT PRINCIPLES (v{principles_version}):
{current_principles}

PRIOR REFINEMENTS:
{refined_findings_text}

KNOWN TENSIONS (do NOT resolve):
{tensions_text}

Produce a shorter version preserving all moral positions."""
