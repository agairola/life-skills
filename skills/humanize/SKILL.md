---
name: humanize
description: >-
  Rewrite AI-sounding text so it reads like a real person wrote it. Produces
  three side-by-side versions at different intensities (Subtle, Human, CEO) so
  the user can pick the one that fits. Use this skill whenever the user pastes
  AI-generated text and asks to "humanize", "de-AI", "make this sound human",
  "fix the AI tone", "remove the LLM voice", or complains that something
  "sounds like ChatGPT/AI/a robot". Also use proactively when the user shares
  an email draft they got from another AI tool and is about to send it.
  Works on any text — emails, LinkedIn posts, Slack messages, cold outreach,
  internal updates, doc paragraphs.
allowed-tools: Read, Write
argument-hint: "[paste the AI text, or path to a file]"
---

# Humanize

Take text that sounds like an AI wrote it and produce three progressively more compressed and more human versions side by side.

## When to use

Trigger whenever the user:
- Pastes text and says "humanize", "de-AI", "make this human", "remove the AI tone"
- Complains "this sounds like ChatGPT / sounds robotic / sounds AI"
- Asks for help rewriting an AI draft before sending
- Asks for variants of an email at different tone levels

Do **not** trigger for: writing new text from scratch, summarising long documents, translating, grammar/spell-checking that's not about AI tone.

## What you produce

Always three versions, in this exact order. The third block's label depends on the input:

```
─── SUBTLE ───
[rewrite]

─── HUMAN ───
[rewrite]

─── CEO ───   (or ─── TIGHT ───, see decision rule below)
[rewrite]
```

**Pick CEO or TIGHT for the third block:**

- **CEO** — default. Use for emails, Slack DMs, asks, replies, cold outreach, short interpersonal messages. Anything where the input is conversational and roughly ≤150 words, or where the entire message is built around a single ask.
- **TIGHT** — use when the input is a substance-heavy long-form post: launch announcement, Show HN, LinkedIn post about a product, technical update, conference recap, anything where the *content itself* is the point and there's no single ask. Heuristic: >150 words, contains named systems / vendors / citations / dates, and doesn't end with a meeting ask or "let me know".

Never produce both CEO and TIGHT in the same output. Pick one based on the input.

No preamble, no closing summary, no "Here are your versions." Just the three blocks. The user wants to compare and pick — don't slow that down with commentary.

If the user explicitly asks for only one level ("give me the CEO version"), produce just that one.

## The mental model

Imagine the same person sending the same message at three different moments of their day:

- **SUBTLE** — they're at their desk, drafted carefully, but cut the corporate fluff before hitting send.
- **HUMAN** — they're between meetings, typed it quickly on their laptop, didn't polish.
- **CEO** — they're walking to a meeting, thumbed it on their phone, sent in 20 seconds.

All three are the same voice, same intent, same person. Just progressively less time spent.

This is important: it is **not** three different personalities. If the input is from a warm, friendly founder, all three outputs should feel like that founder at different speeds — not Subtle=corporate-lawyer / Human=casual-PM / CEO=blunt-exec. Preserve the sender's voice; just strip AI tells and compress.

## Universal rules (apply to all three versions)

### Preserve

- Every specific fact, name, number, date, URL, or proper noun from the original — copy them verbatim
- The core ask or call-to-action
- Urgency level and any implied deadline
- The relationship implied by the original (peer-to-peer, customer-to-vendor, boss-to-report, cold outreach, etc.)

If you can't tell whether something is a "fact to preserve" or "fluff to cut", err on preserving it. Losing a name or a date is worse than leaving in a slightly stilted sentence.

### Prefer

- Direct language ("we should talk" beats "I believe a conversation would be valuable")
- Natural contractions (don't, can't, we're, I'd) — humans use them; AI often doesn't
- Uneven sentence length — mix short punchy sentences with longer ones
- Active voice
- Concrete nouns over abstract ones ("the migration" beats "the strategic initiative")

### Avoid — phrases

Never let any of these survive in any tone:

- "I hope this email finds you well"
- "I wanted to reach out"
- "Please don't hesitate to..."
- "Please let me know" / "Please advise"
- "What works for your schedule" / "Let me know what works for you" / "What works on your end" / "Let me know your availability"
- "At your earliest convenience"
- "Moving forward" / "Going forward"
- "Synergy" / "Synergies"
- "Leverage" as a verb (use "use")
- "Utilize" (use "use")
- "Circle back" / "Touch base"
- "I believe there is significant value in..."
- "It is worth noting that..."
- "Furthermore," "Moreover," "Additionally," at the start of a sentence
- "In conclusion" / "To summarize"
- "Delve into" / "Delving"
- "Stands as a testament to"
- "Plays a vital role"
- "Underscores the importance of"
- "Quietly [revolutionizing/transforming/changing]"
- "Best regards" — use "Thanks", "Cheers", or just the name

### Avoid — structures (this is where most humanizers fail)

These are patterns, not phrases. Watch for **all variants** — verb tense doesn't matter, the pattern does.

- **The "not just X, it's Y" family** — *the* single most recognizable AI cadence. Includes ALL of these forms — they're the same pattern wearing different verbs:
  - "It's not just X, it's Y"
  - "It's not about X, it's about Y"
  - "X doesn't just do Y, it does Z" *(e.g., "Sentinel doesn't just flag threats, it helps teams understand them")*
  - "X isn't just Y, it's Z"
  - "Not only X, but also Y" / "Not only does X, but also Y"
  - "More than [just] X — Y"

  Whenever you see this shape, kill it. Pick one side and state it directly. **Rewrite examples:**
  - ❌ "Sentinel doesn't just flag threats, it helps teams understand them."
  - ✅ "Sentinel flags threats and explains why each one matters."
  - ❌ "It's not just about catching bugs — it's about preventing them."
  - ✅ "We catch bugs early so they don't ship."

- **Rule of three (any three abstract nouns/adjectives in a list)** — even when the three words aren't perfect synonyms, a tidy noun-noun-and-noun list is a fingerprint. Cut to one specific concrete claim, or pick the strongest two. **Rewrite examples:**
  - ❌ "trustworthiness, transparency, and resilience"
  - ✅ "we tell you what we're doing and why" (concrete) or "transparency and resilience" (two)
  - ❌ "credibility, trustworthiness, and integrity"
  - ✅ pick one, or replace with the actual proof point ("a five-year clean audit record")
  - ❌ "scalable, reliable, and efficient"
  - ✅ "handles 10× our current load on the same hardware"

  Even if the three words are technically distinct, the *shape* (three short abstract terms separated by commas with "and") is the tell. If you find one, you must rewrite — don't just reword.

- **Present-participle padding** — sentences ending with ", ensuring X" / ", highlighting Y" / ", reflecting Z" / ", enabling W" / ", empowering V" / ", allowing U". Cut the participle. Split into a separate sentence if the point matters; otherwise drop it.
- **False ranges** — "from startups to enterprises", "from X to Y" when X and Y aren't a real spectrum. Just name what you mean ("works for small teams and big ones" → or just don't say it).
- **Em dashes** — replace with periods, commas, or parentheses. Em dashes scream AI now. Hyphens are fine; em dashes (—) are not.
- **Editorializing adverbs** — "quietly", "fundamentally", "increasingly", "remarkably", "truly", "deeply". Usually deletable.
- **Throat-clearing openers** — "I wanted to...", "Just reaching out to...", "I'm writing to...", "I hope...". Start with the actual content.
- **Tidy paragraph length** — if every paragraph is 3 sentences and feels balanced, it reads as AI. Break the symmetry.

When in doubt, ask: "Would a real person actually type this phrase?" If no, rewrite it.

## Per-tone specs

### SUBTLE

**Target:** still polished, still work-appropriate, just trimmed and de-roboticized.

**Length:** roughly the same as the original, or 10–15% shorter.

**Style:**
- Keep the overall *layout*: same paragraphs, same greeting/sign-off if the original had them
- Replace formal phrasing with normal phrasing
- Use contractions where natural
- Remove the avoid-list phrases and structures — **including the structural ones**. "Keep the structure" means keep the *shape of the message* (greeting, paragraphs, sign-off), NOT keep AI sentence-patterns. If the input has a "doesn't just X, it Ys" sentence or a three-noun list, those still get rewritten in SUBTLE. SUBTLE is the most polished tone — it is not "the lightest touch on AI tells."
- Keep it readable and professional — this version is what you'd send to a customer or a stranger

**Don't:**
- Don't make it casual
- Don't add fragments
- Don't insert typos
- Don't change the greeting or sign-off style if the original had one

It should read like: *"I wrote this myself and cut the nonsense."*

---

### HUMAN

**Target:** fast, natural, like a real person typed it between meetings without overthinking.

**Length:** 20–30% shorter than the original. Compress.

**Style:**
- Shorter sentences. Fragments are allowed.
- Start with the actual content — drop the "I wanted to..." opener
- Light hedging is welcome where a human would hedge: *I think, probably, might be worth, honestly, not sure if*
- At most one casual connector if it fits the voice: *honestly, anyway, to be fair, fwiw, tbh*
- Allow one small imperfection somewhere in the message (not always in the first sentence — a real human's typos appear unpredictably):
  - a missing apostrophe (`dont`, `cant`, `wont`)
  - a dropped comma a careful writer would have added
  - a slightly clipped phrase
  - a doubled small word ("the the") — rare
  - **Skip the imperfection entirely if the input is high-stakes** (legal, exec comms, customer complaint reply). Better no imperfection than a fake one.
- Sign off naturally if the original had a sign-off: *Thanks, Cheers, or just the name*. If the original had no sign-off, don't add one.

**Don't:**
- Don't make it messy or hard to read
- Don't pile on slang
- Don't sound try-hard casual ("yo", "hey friend") unless the original was already that casual

It should read like: *"I said the thing and didn't overwork it."*

---

### CEO

**Target:** short, blunt, mobile-typed during something else.

**Length:** 30–50% of the original. Aggressively cut.

**Style:**
- 1 to 4 sentences, max
- All lowercase is fine but not mandatory — only force lowercase if the input is casual to begin with; for a formal input, sentence case CEO mode still reads as "busy exec" without screaming "I used a humanizer"
- Drop "I" where natural ("think we should talk" instead of "I think we should talk")
- Fragments are good
- No greeting unless the original absolutely required one (e.g., a formal letter)
- Simple punctuation only — periods, question marks, the occasional comma
- Abbreviations are fine where they fit: `lmk`, `fyi`, `tbh`, `asap`, `pls`, `thx`
- **Sign-off:** only append `Sent from my iPhone` if the original had a signature *and* removing the signature would lose information. If the original was unsigned, leave the CEO version unsigned too — the always-on "Sent from my iPhone" is now itself an AI-humanizer fingerprint.

**Don't:**
- Don't strip out the actual ask or key facts to hit the length target — compress around them, not through them
- Don't add personality the original didn't have ("haha", emoji, "lol")
- Don't force lowercase on every input

It should read like: *"sent fast from a phone during something else."*

---

### TIGHT

(Use TIGHT instead of CEO when the input is a substance-heavy long-form post. See "What you produce" for the decision rule.)

**Target:** the same announcement, written by someone who doesn't pad. Mobile-fast voice on a long post. Substance survives intact; tone changes.

**Length:** ~70–85% of the original. Trim adjectives, hedges, throat-clearing, and connective tissue. Do **not** cut named systems, vendors, regulations, dates, citations, links, or proper nouns. If you can't get under 85% without dropping one of those, stop at 90% — the length target is a guide, the substance rule is a hard constraint.

**Style:**
- Keep the paragraph structure. Every paragraph in the input should have a corresponding paragraph in TIGHT.
- Shorter sentences than the original. One claim per sentence — no multi-claim sentences glued with "while also" / "in addition to".
- Drop puffery adjectives: *seamless, comprehensive, robust, powerful, cutting-edge, world-class, innovative*. The thing being described is the proof; the adjective is filler.
- Direct verbs: *ships, uses, stores, sends, runs, blocks*. Not *leverages, enables, facilitates, empowers*.
- Drop editorializing adverbs (*quietly, fundamentally, truly, remarkably*) and softening hedges (*it's worth noting that, I think it's important to mention*).
- Keep lists as lists. Keep inline links. Keep code/identifier formatting.
- Match the original's register — if the input is technical, TIGHT stays technical. If casual, TIGHT stays casual.

**Don't:**
- Don't summarize. TIGHT is not a TL;DR. If a paragraph in the input had three technical claims, TIGHT has three technical claims — said in fewer words each, not collapsed into one.
- Don't soften technical specifics to make prose flow. "Stored in a local-only SwiftData store" stays as is — don't rewrite to "kept on-device" if the input named the system.
- Don't insert manufactured typos. TIGHT is for public/high-stakes content where fake imperfections would undermine credibility.
- Don't add personality the original didn't have.
- Don't append a signature the original didn't have.

It should read like: *"the same post, with every padding word removed."*

## Transformation rules

These override the per-tone specs when they conflict:

- **If the input is already short (under ~50 words):** don't inflate any version. SUBTLE may be nearly identical to the input. HUMAN trims lightly. CEO can still be 1–2 sentences.
- **If the input is already casual:** don't over-clean SUBTLE into formality. Just remove AI tells.
- **If the input contains a clear call-to-action:** the CTA must survive all three versions, made progressively more direct.
- **If the input contains a vague pitch ("synergies", "explore opportunities"):** force concreteness — what specifically is being asked for? If you genuinely can't tell, say so in plain language ("not sure exactly what you're proposing — want to jump on a quick call?") rather than echoing the vagueness.
- **If the input has bullet points or a list:** keep the list in SUBTLE, may flatten to prose in HUMAN, definitely flatten in CEO unless the list is the entire message. **TIGHT keeps lists as lists.**
- **If the input is a substance-heavy long-form post** (>150 words, content not ask — launch posts, Show HN, technical updates, LinkedIn announcements): use TIGHT instead of CEO as the third block. The preserve list grows: every named system, vendor, regulation, date, citation, and link must survive all three versions. Failing this turns the skill into a summarizer — different tool, wrong job.

## Worked example

**Input:**
> I wanted to reach out to express my interest in connecting regarding potential synergies between our organizations. I believe there is significant value in exploring how we might collaborate moving forward. Please let me know if you would be available for a brief call at your earliest convenience.

**Output:**

```
─── SUBTLE ───
Wanted to see if there's a fit between our teams. I think we could work well together and it'd be worth a short call to explore. Free for 20 minutes next week?

─── HUMAN ───
Think we'd work well together — worth a quick call? Got 20 mins free next week?

─── CEO ───
think we should connect. quick call this week?
```

Notice: no em-dashes, no "synergies", no "moving forward" / "going forward", no "at your earliest convenience", no "Please let me know", no "what works on your end". CEO version dropped the "Sent from my iPhone" — the original had no signature, so adding one would be a fingerprint. The HUMAN version kept the substance and asked for a specific time-box ("20 mins"). SUBTLE preserved the layout (one paragraph, polite-but-direct ask) but stripped the corporate phrasing.

(Notice also: the example deliberately does NOT use "going forward" or "what works on your end" — those are common humanizer outputs that themselves became fingerprints. Don't reach for them.)

## Worked example — long-form post (TIGHT path)

**Input** (235 words, launch post — triggers TIGHT, not CEO):
> Today, I'm thrilled to announce the launch of Cinder — a build cache that's quietly transforming how teams ship CI pipelines.
>
> In building Cinder, we focused on three core principles: speed, reliability, and developer experience. Cinder doesn't just cache build artifacts — it understands the dependency graph of your monorepo and invalidates intelligently. Whether you're a small startup or a Fortune 500 enterprise, Cinder meets you where you are.
>
> Under the hood, Cinder uses content-addressed storage backed by S3 and Cloudflare R2, with a Rust daemon that hashes artifacts in parallel. Honeycomb's 2023 Buildkite outage study showed that roughly 40% of CI cost is wasted recomputation — we're going after that.
>
> We're proud to share that early adopters at Linear and Vercel are seeing build times drop by 60%, ensuring their teams ship faster than ever.
>
> Try it free at cinder.dev/start. If you're navigating CI pain, we'd love to chat.

**Output:**

```
─── SUBTLE ───
Launching Cinder today. It's a build cache for monorepo CI pipelines that hashes your dependency graph and invalidates artifacts intelligently.

Under the hood, Cinder uses content-addressed storage backed by S3 and Cloudflare R2, with a Rust daemon that does the hashing in parallel. Honeycomb's 2023 Buildkite outage study put wasted recomputation at roughly 40% of CI cost, and that's the target.

Early adopters at Linear and Vercel are seeing build times drop by about 60%.

Try it at cinder.dev/start. Happy to chat if you're working through CI pain.

─── HUMAN ───
Shipped Cinder today. Build cache for monorepo CI.

Hashes the dependency graph and invalidates artifacts intelligently. Content-addressed storage on S3 + R2, Rust daemon doing the hashing in parallel.

Honeycombs 2023 Buildkite outage study put wasted recomputation at ~40% of CI cost. Thats the wedge.

Linear and Vercel are seeing builds drop ~60% so far.

cinder.dev/start. Glad to talk CI if youre stuck.

─── TIGHT ───
Launched Cinder. A build cache for monorepo CI pipelines.

Cinder hashes the dependency graph and invalidates artifacts intelligently. Storage is content-addressed and backed by S3 plus Cloudflare R2. A Rust daemon does the hashing in parallel.

Honeycomb's 2023 Buildkite outage study put wasted recomputation at roughly 40% of CI cost. That's the target.

Early adopters at Linear and Vercel are seeing build times drop 60%.

Try it at cinder.dev/start. Happy to answer CI questions.
```

Notice: every named system (Cinder, S3, Cloudflare R2, Rust, Honeycomb, Buildkite, Linear, Vercel), the date (2023), the citation (Buildkite outage study), the link (cinder.dev/start) and the specific number (40%, 60%) survive in all three. The em-dashes from the input are gone everywhere. The "not just cache, it understands" sentence is broken into two direct claims. The triplet "speed, reliability, and developer experience" is dropped — it added nothing the rest of the post doesn't prove. HUMAN drops three apostrophes (`Honeycombs`, `Thats`, `youre`) as its small imperfections; TIGHT does not (high-stakes launch post). TIGHT is the same length as HUMAN here — they differ in *register*, not bytes: HUMAN sounds between-meetings, TIGHT sounds like a senior writer who doesn't pad. CEO would have collapsed this to 4 sentences and dropped half the named systems — wrong tool for this input.

## Anti-patterns to actively avoid

- **Inserting the same typo every time** — if HUMAN always has the typo in the first two words, that's a fingerprint of the skill, not a sign of a human. Vary placement, vary type, or skip it.
- **Auto-appending "Sent from my iPhone" to every CEO output** — also a fingerprint. Only include if it fits.
- **Producing three outputs that read like three different people** — they should be the same voice at three speeds.
- **Adding warmth the original didn't have** — if the input was blunt, don't make SUBTLE friendly. Match register.
- **Replacing one cliché with another** — don't swap "synergy" for "alignment" or "leverage" for "harness". Use plain words.
- **Echoing the marketing-site demo verbatim** — that specific "I wanted to reach out about potential synergies..." input has been used in every humanizer demo. Don't memorize it; apply the principles to whatever the user actually pasted.

## Two-pass critique before output

Single-shot rewrites miss their own AI tells — models acknowledge "no em-dashes" then produce em-dashes in the same response. Do this in two passes for each version before you commit to output.

**Pass 1 — answer in one sentence: "what in this draft would a reader flag as AI?"**

Force yourself to name something specific. "Looks fine" is never the right answer on the first read — there is always something. Use the catalogue below as the vocabulary:

- An em-dash (—) anywhere — this is the most common silent failure
- A "not just X, it's Y" / "doesn't just X, it Ys" / "isn't just X, it Ys" / "not only X, but Y" sentence
- A three-item list of abstract nouns or adjectives ("trust, transparency, and resilience")
- A sentence ending with ", ensuring/highlighting/reflecting/enabling/empowering/allowing X"
- A banned phrase: search for *synergy, circle back, moving forward, going forward, hope this, don't hesitate, earliest convenience, let me know, what works, delve, leverage, utilize*
- (CEO only) An auto-appended "Sent from my iPhone" when the original had no signature
- (TIGHT only) A named system, vendor, regulation, citation, or link from the input that didn't survive
- Three versions that read like three different people instead of one person at three speeds

**Pass 2 — rewrite only what Pass 1 named.** If Pass 1 said "em-dash in sentence 2 of SUBTLE", fix that specifically. Don't rewrite the whole block — that just produces a new set of tells.

If Pass 1 honestly turns up nothing after a careful read, ship the draft. The critique is there to catch what you missed, not to manufacture changes.

## Em-dash gate (non-negotiable final check)

After the two-pass critique, scan each block character-by-character for the em-dash character `—` (Unicode U+2014). If you find any, replace each with a period, comma, or pair of parentheses based on context, then re-scan.

Hyphens (`-`) are fine. En-dashes (`–`, U+2013) in number ranges are fine. The character to hunt is `—`.

This gate exists separate from the critique because models acknowledge "no em-dashes" instructions and then output them anyway in the same response. Treat the scan as a deliberate final step, not a passive rule. Skipping it is what every other humanizer does — and it's why their outputs still read as AI.

## If the input isn't AI-sounding

If the user pastes text that already reads as human, say so plainly and ask if they want you to push for further compression or specific changes. Don't invent AI tells to "fix."

## If the input is in another language

Same three-tone treatment, applying the same principles (cut AI tells, compress progressively) in that language. The avoid-list above is English-specific — the *patterns* (corporate triplets, present-participle padding, em-dashes, "not X, it's Y") translate to most languages and should still be hunted down.
