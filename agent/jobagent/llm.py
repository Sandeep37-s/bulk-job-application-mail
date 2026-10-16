"""LLM calls: pick out companies from search results, and write the email."""
import json
import logging

from openai import AzureOpenAI, OpenAI

from .config import CFG, env

log = logging.getLogger(__name__)

if env("AZURE_OPENAI_ENDPOINT"):
    _client = AzureOpenAI(azure_endpoint=env("AZURE_OPENAI_ENDPOINT"), api_key=env("AZURE_OPENAI_API_KEY"),
                          api_version=env("AZURE_OPENAI_API_VERSION", "2024-10-21"))
    _model = env("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
else:
    _client = OpenAI(api_key=env("OPENAI_API_KEY") or "missing", base_url=env("OPENAI_BASE_URL") or None)
    _model = env("OPENAI_MODEL", "gpt-4o-mini")


def ask_json(system, user, temperature=0.2):
    resp = _client.chat.completions.create(
        model=_model, temperature=temperature, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return json.loads(resp.choices[0].message.content)


EXTRACT_SYSTEM = """You find small AI companies in India that could hire an AI/ML engineer.
From the web search results, list each distinct COMPANY (not job boards, not news sites, not
training institutes) that appears to be located in one of these cities: {cities}.
Return JSON: {{"companies": [ {{
  "company": str,
  "website": str or null      (the company's own site, e.g. "acme.ai"; never a job-board URL),
  "city": str or null,
  "what_they_do": str         (one sentence on their product/domain),
  "is_ai_company": bool       (core product is AI/ML/GenAI/data),
  "est_employees": int        (always give your best estimate; well-known/large firms = their real size),
  "hiring_role": str or null  (an AI/ML/data role they are advertising, if the result shows one),
  "job_url": str or null,
  "contact_email": str or null (only if literally present in the result text),
  "why": str                  (one line: why this company is worth emailing)
}} ] }}
Only include facts supported by the results. If nothing qualifies return {{"companies": []}}."""


def extract_companies(results):
    if not results:
        return []
    text = "\n\n".join(f"[{i}] {r['title']}\nURL: {r['url']}\n{r['snippet']}" for i, r in enumerate(results))
    system = EXTRACT_SYSTEM.format(cities=", ".join(CFG["search"]["cities"]))
    try:
        return ask_json(system, text).get("companies", [])
    except Exception as e:
        log.warning("extraction failed: %s", e)
        return []


COMPOSE_SYSTEM = """You write short cold job-application emails for {name}.
Rules:
- 90-140 words in the body (signature not counted). Plain text, no markdown, no emojis, no placeholders.
- Sound like a person, not a template: no "I am impressed by", "I am excited", "aligns with my passion".
- Start with "Hi {{greeting}}," using the greeting given.
- First line: something specific about what the company builds, so it is clearly not a mass email.
- If a hiring role is given, apply for that role by name. Otherwise ask whether they have
  openings for an AI/GenAI engineer and say why their domain interests him.
- Pick the 2-3 facts from his background that best match their domain. Use ONLY the facts below;
  never invent numbers, employers, skills or achievements. Keep each piece of work tied to
  the employer it was done at (e.g. the RAG system was at NIC). Say nothing about his work at
  Dhruva Technology beyond his job title there.
- Mention the resume is attached. End with a one-line call to action, then the signature:
{signature}
- Subject: under 9 words, specific to the role or company.
Background facts:
{facts}
Return JSON: {{"subject": str, "body": str}}"""


def compose_email(lead, site_text, extra_instruction=""):
    p = CFG["profile"]
    signature = "\n".join(x for x in [
        "Best regards,", p["name"], p["current_role"], p["phone"], p["email"], p.get("linkedin"), p.get("github"),
    ] if x)
    system = COMPOSE_SYSTEM.format(name=p["name"], signature=signature, facts=p["facts"])
    user = json.dumps({
        "company": lead["company"],
        "what_they_do": lead.get("what_they_do"),
        "hiring_role": lead.get("hiring_role"),
        "greeting": greeting_for(lead.get("email", "")),
        "company_website_text": (site_text or "")[:2500],
        "extra_instruction": extra_instruction,
    }, ensure_ascii=False)
    out = ask_json(system, user, temperature=0.6)
    return out["subject"].strip(), out["body"].strip()


def greeting_for(email):
    local = email.split("@")[0].lower()
    if any(k in local for k in ("hr", "career", "job", "talent", "hiring", "recruit", "people")):
        return "Hiring Team"
    return "Team"
