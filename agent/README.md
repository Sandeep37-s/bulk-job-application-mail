<div align="center">

# 🤖 AI Job-Hunt Agent

**Finds small AI startups in Delhi & Noida, writes each one a tailored application, and sends it from your Gmail — but only after you tap ✅ on Telegram.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-gpt--4.1--mini-0078D4?logo=microsoftazure&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-approval%20bot-26A5E4?logo=telegram&logoColor=white)
![Gmail](https://img.shields.io/badge/Gmail-SMTP-EA4335?logo=gmail&logoColor=white)
![Runs on](https://img.shields.io/badge/runs%20on-Azure%20VM-0078D4?logo=ubuntu&logoColor=white)

</div>

---

## Why

Big companies route applications through portals and ATS filters. Small AI startups often don't have a hiring pipeline at all — a short, specific email to the right inbox gets read. Finding those startups, their real contact address and what they build, then writing a non-generic email for each, is hours of work a day. This agent does that part, and leaves the decision to you.

## How it works

```mermaid
flowchart LR
    A[⏰ Every 3 h] --> B[🔎 Web search<br/>job posts · startup lists ·<br/>Wellfound · Cutshort · LinkedIn]
    B --> C[🧠 LLM picks companies<br/>AI-focused · &lt;200 people ·<br/>Delhi / Noida only]
    C --> D[🌐 Visit company site<br/>read what they build ·<br/>find careers@ / hr@ email]
    D --> E[✍️ LLM drafts email<br/>matched to their domain,<br/>only real facts from your profile]
    E --> F{📱 Telegram card}
    F -- ✅ Send --> G[📧 Gmail + resume.pdf]
    F -- 🔁 Rewrite --> E
    F -- ❌ Skip --> H[🗂 never shown again]
```

Every card tells you **why** that company was picked and **where** the address came from:

```text
Acme Vision AI · Noida            (example)
🔵 AI company (no posted opening — writing to HR)
🏢 Builds document-understanding APIs for Indian banks
💡 Small Noida AI startup working on LLMs and OCR
🌐 https://acmevision.example
✉️ To: careers@acmevision.example
   found on: https://acmevision.example/careers

Subject: GenAI engineer – RAG and search experience

Hi Team,
...
        [ ✅ Send ]   [ 🔁 Rewrite ]   [ ❌ Skip ]
```

Reply to a card with *"shorter"* or *"mention my computer-vision project"* to get a rewrite, or with `to: founder@company.com` to change the recipient.

## Features

| | |
|---|---|
| 🎯 **Targeted** | Small AI companies only; big-company and job-board blocklist; city filter |
| ✋ **Human-in-the-loop** | Nothing is sent until you approve it on Telegram |
| 🧾 **No invented facts** | Drafts may only use the facts listed in `config.yaml` |
| 📬 **Real addresses** | Emails are scraped from the company's own site; LLM-reported addresses are dropped unless they appear verbatim in the source |
| 🔁 **Never twice** | One row per company domain in SQLite — nobody is contacted twice |
| 🐢 **Inbox-safe** | Daily cap (20) and a gap between sends to keep your Gmail out of spam |
| ☁️ **Always on** | systemd service on a free-tier Azure VM, no inbound ports |

## Can someone use this repo to send email from my account?

**No.** The repo contains code only. Everything that could send mail is in `agent/.env`, which is git-ignored and exists only on your machine and your server:

- the **Gmail app password** — without it, SMTP login fails;
- the **Telegram bot token** and **your chat id** — the bot ignores every chat except yours, so a stranger who finds the bot can't trigger a send;
- the **Azure OpenAI key**.

Anyone who clones the repo has to supply their own Gmail, bot and LLM keys, and can only ever send from *their* account. If a secret ever leaks: revoke the app password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), send `/revoke` to @BotFather, and regenerate the Azure key.

## Use it yourself

```bash
cd agent
pip install -r requirements.txt
cp .env.example .env          # fill in Gmail app password, Telegram token, LLM key
python main.py --whoami       # message your bot first; prints your chat id → .env
python main.py --dry-run      # one search cycle, prints drafts, sends nothing
python main.py                # run the bot + scheduler
```

Edit `config.yaml` for your own profile facts, cities, search queries and limits, and `resume/build_resume.py` for your resume (`python resume/build_resume.py` rebuilds the PDF).

**Telegram commands:** `/run` search now · `/pending` drafts waiting · `/stats` · `/pause` · `/resume`

### Deploy to Azure

```bash
az login
bash deploy/azure/deploy.sh   # creates the VM on first run; later runs push code + .env and restart
```

Creates an Ubuntu VM (free-tier size), installs the agent as a systemd service, and opens no inbound ports — the bot only makes outbound connections.

## Project layout

```
agent/
  main.py              Telegram bot, approval buttons, scheduler
  config.yaml          profile facts, cities, queries, filters, send limits
  jobagent/
    search.py          DuckDuckGo / Tavily search + page fetch
    llm.py             company extraction and email drafting (Azure OpenAI or any OpenAI-compatible API)
    contacts.py        website discovery, email scraping and ranking, blocklists
    pipeline.py        one search → filter → scrape → draft cycle
    mailer.py          Gmail SMTP with resume attachment
    db.py              SQLite: companies, statuses, seen URLs
  resume/              resume source + generated PDF
deploy/azure/          VM deploy script + systemd unit
```
