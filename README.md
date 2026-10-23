<div align="center">

<a href="agent/README.md"><img src="agent/assets/hero.svg" alt="AI Job-Hunt Agent" width="100%"></a>

# Bulk Job-Application Mail

**Two ways to send job applications from your own Gmail — an autonomous AI agent, and a bulk-send web app.**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-0078D4?style=for-the-badge&logo=microsoftazure&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Gmail](https://img.shields.io/badge/Gmail-EA4335?style=for-the-badge&logo=gmail&logoColor=white)

![license](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![agent tests](https://img.shields.io/badge/agent_tests-50_passing-2ea44f?style=flat-square)

</div>

---

<table>
<tr>
<td width="50%" valign="top">

### 🤖 [AI Job-Hunt Agent](agent/README.md)

Runs 24/7 on an Azure VM. Finds AI/ML openings and AI startups in Delhi NCR, screens out senior roles and fake posts, writes a tailored email for each, and sends **40 a day** from your Gmail, the soonest deadline first.

`Python` · `Azure OpenAI` · `Telegram` · `SQLite`

**[→ Read the agent docs](agent/README.md)**

</td>
<td width="50%" valign="top">

### 📨 Dispatch web app

Upload or paste a recipient list, write one template with `{{name}}` / `{{company}}` / `{{position}}`, preview every email, attach your resume, and send in bulk from the browser.

`Next.js` · `React` · `Gmail API` · `NextAuth`

**[→ Jump to Dispatch](#-dispatch--bulk-email-from-your-browser)**

</td>
</tr>
</table>

<p align="center"><img src="agent/assets/pipeline.svg" alt="How the agent works" width="100%"></p>

## 🤖 Agent at a glance

| | |
|---|---|
| 🎯 **Relevant roles only** | AI / ML / GenAI / LLM / NLP / CV / MLOps / data science. No office, HR or sales jobs |
| 🧑‍🎓 **Right level** | 0–2 years or fresher. Senior, Lead, Head, Architect and 3+ year roles are skipped before drafting |
| 🏢 **Employers only** | recruitment agencies, staffing firms and job portals are skipped |
| 🛡️ **Fake-post filter** | fee requests, guaranteed jobs, "earn ₹X/day", WhatsApp-only applications are rejected |
| ⏳ **Deadline-first** | earliest deadline sent first; expired jobs never sent; Telegram alert if one may be missed |
| 🐢 **Inbox-safe** | 40/day in working hours (09:30–19:30 IST, Mon–Sat), ~13 min apart with random spacing, never the same address twice |
| 💸 **Cost-aware** | sleeps once the day is covered; caches repeated AI work |

```bash
cd agent && pip install -r requirements.txt && cp .env.example .env
python main.py --dry-run     # one search cycle, sends nothing
```

Full setup, screening rules, Telegram commands and Azure deploy are in **[agent/README.md](agent/README.md)**.

---

## 📨 Dispatch — bulk email from your browser

Send personalised job-application emails to many recruiters, one click at a time, directly from your own Gmail account.

### Features

| | |
|---|---|
| 🔐 **Sign in with Google** | OAuth 2.0, only the `gmail.send` scope; sends from your own account |
| 📋 **Recipients** | paste many addresses or import a CSV; duplicate and invalid rows flagged |
| 📝 **Templates** | `{{name}}`, `{{company}}`, `{{position}}` placeholders; conservative automatic greetings |
| 📎 **Attachments** | resume plus extra files on every email |
| 👀 **Preview** | step through each recipient's exact email and edit before sending |
| ⏱️ **Pacing** | configurable delay, daily counter with limit warning |
| 🗂️ **History** | searchable send history, one-click retry of failures, CSV export |
| 💾 **No database** | everything stays in your browser's `localStorage` |

### Quick start

```bash
npm install
npm run dev             # http://localhost:3000
```

Create a `.env` in the repo root (see *Environment variables* below). You need a Google Cloud OAuth client with the Gmail API enabled first. It takes about five minutes:

<details>
<summary><b>☁️ Google Cloud setup (OAuth + Gmail API)</b></summary>

The application uses **Google OAuth 2.0** and the **Gmail API** to send
emails through the user's Gmail account. You must configure Google Cloud
before running the app — this takes about five minutes.

#### 1. Create a Google Cloud project

Open [console.cloud.google.com](https://console.cloud.google.com/) and
create a new project, e.g. `Dispatch Email Sender`. Make sure the new
project is selected before continuing.

#### 2. Enable the Gmail API

**Google Cloud Console → APIs & Services → Library** → search `Gmail API`
→ **Enable**. If it already says "Manage" instead of "Enable", it's
already on.

#### 3. Configure the OAuth consent screen

Go to **Google Cloud Console → Google Auth Platform**. Depending on your
console version this is organized into sections like *Branding*,
*Audience*, *Data Access*, and *Clients*.

- **Branding** — set an app name (e.g. `Dispatch Email Sender`) and a
  support/contact email.
- **Audience** — for personal development/testing, choose **External**.
  While the app is in **Testing** publishing status, add the Gmail
  account(s) you'll sign in with under **Test users** — only those
  accounts can authenticate until the app is verified or published.
- **Data Access → Add or remove scopes** — add:

  ```
  https://www.googleapis.com/auth/gmail.send
  ```

  shown as "Send email on your behalf." Make sure the checkbox is
  selected and save.

  > **Important:** the app requires `gmail.send`. Do not substitute
  > `gmail.compose` — the code calls `gmail.users.messages.send`, which
  > needs the send scope specifically.

#### 4. Create an OAuth Client ID

**Google Cloud Console → APIs & Services → Credentials → + Create
Credentials → OAuth client ID**.

- Application type: **Web application**
- Name: e.g. `Dispatch Web Client`
- **Authorized JavaScript origins**: add `http://localhost:3000`
- **Authorized redirect URIs**: add exactly:

  ```
  http://localhost:3000/api/auth/callback/google
  ```

  This must match **exactly** — no trailing slash, no `https://` instead
  of `http://`, no `127.0.0.1` instead of `localhost` (unless that's
  genuinely what you're browsing to). For production, also add:

  ```
  https://YOUR-DOMAIN.com/api/auth/callback/google
  ```

Copy the generated **Client ID** and **Client Secret** — you'll need them
in `.env` below.

</details>

<details>
<summary><b>🔑 Environment variables</b></summary>

Create a `.env` file in the project root:

```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
NEXTAUTH_SECRET=your_generated_secret
NEXTAUTH_URL=http://localhost:3000
```

| Variable | Where to get it |
|---|---|
| `GOOGLE_CLIENT_ID` | Google Cloud Console → Credentials → your OAuth Client |
| `GOOGLE_CLIENT_SECRET` | Same OAuth Client page |
| `NEXTAUTH_SECRET` | Generate with `openssl rand -base64 32` (see note below) |
| `NEXTAUTH_URL` | `http://localhost:3000` locally, your real domain in production |

If `openssl` isn't available (e.g. some Windows setups), generate a long
random string with any trusted method — a password manager's generator
works fine — and use that instead.

</details>

<details>
<summary><b>📦 Installation</b></summary>

```bash
npm install
npm run dev
```

Open `http://localhost:3000`, click **Sign in with Google**, and sign in
with the account you added as a **Test user**. Accept the "Send email on
your behalf" permission when prompted.

</details>

<details>
<summary><b>🩺 OAuth troubleshooting</b></summary>

These are the actual errors you're likely to hit and how to fix each one.

#### `Error 400: redirect_uri_mismatch`

**Cause:** the redirect URI NextAuth sends doesn't exactly match what's
registered in Google Cloud.

**Fix:**
1. Google Cloud → APIs & Services → Credentials → your OAuth Client →
   Authorized redirect URIs → add exactly
   `http://localhost:3000/api/auth/callback/google`.
2. Confirm `.env` has `NEXTAUTH_URL=http://localhost:3000` with no
   trailing slash and matching protocol/port.
3. Save in Google Cloud, then restart `npm run dev` (env and OAuth client
   changes aren't picked up by hot-reload).

#### `Error 403: access_denied`

**Cause:** the Google account you're signing in with isn't registered as
a test user while the app is in Testing mode.

**Fix:** Google Auth Platform → Audience → Test users → add that Gmail
address → sign in again.

#### `Request had insufficient authentication scopes` / `Insufficient Permission` (Gmail API 403)

This is the one that shows up as a `500` from `/api/send` with a Gmail
`GaxiosError: Insufficient Permission` in your terminal. It means the
access token your browser session is holding doesn't actually carry the
`gmail.send` scope — usually because you signed in *before* the scope was
correctly configured, and Google is still handing back an old-style
token.

**Cause:** the Google access token in your current session was issued
without the `gmail.send` scope.

**Fix, in order:**
1. Confirm the scope is really enabled: Google Auth Platform → Data
   Access → make sure `https://www.googleapis.com/auth/gmail.send` is
   checked, and save.
2. **Sign out of the app** (top-right → Sign out).
3. Revoke the app's existing access so Google issues a fresh token:
   go to [myaccount.google.com/permissions](https://myaccount.google.com/permissions),
   find this app, and remove its access.
4. Sign in again. Google should now explicitly show the "Send email on
   your behalf" permission during consent — if it doesn't ask for that
   permission, the scope still isn't wired up correctly upstream.

> **The lesson here:** changing the scope in `lib/auth.ts` only changes
> what *new* sign-ins request. It does not retroactively upgrade a token
> a browser session already has cached. Any time you change OAuth scopes
> in Google Cloud or in code, you need to sign out, revoke prior access
> at myaccount.google.com/permissions, and sign in again — otherwise
> you'll keep hitting `insufficient_scope` even though the config looks
> right.

#### Debugging `/api/send` 500s in general

A bare `POST /api/send 500` in your terminal doesn't show *why* Gmail
rejected the request. `app/api/send/route.ts` logs the full Gmail API
error to the server console specifically so you can see the real reason
— look for the block between `===== GMAIL SEND ERROR =====` and `====`
in your terminal output, and check the `error.response.data.error`
field for Gmail's actual message (e.g. `insufficientPermissions`,
`invalid_grant`, rate-limit errors, etc.).

</details>

<details>
<summary><b>✅ Troubleshooting checklist</b></summary>

If sign-in or sending isn't working, check each of these:

- [ ] Gmail API is enabled on the correct Google Cloud project
- [ ] OAuth consent screen (Branding/Audience/Data Access) is fully configured
- [ ] Your Gmail account is added as a Test user
- [ ] The `gmail.send` scope is added and saved under Data Access
- [ ] OAuth Client ID (Web application) exists
- [ ] Authorized JavaScript origin is `http://localhost:3000`
- [ ] Authorized redirect URI is exactly `http://localhost:3000/api/auth/callback/google`
- [ ] `.env` has correct `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
- [ ] `.env` has a real `NEXTAUTH_SECRET`
- [ ] `.env` has `NEXTAUTH_URL=http://localhost:3000`
- [ ] Dev server was restarted after any `.env` or Google Cloud change
- [ ] After changing scopes: signed out, revoked access at
      [myaccount.google.com/permissions](https://myaccount.google.com/permissions),
      and signed in again
- [ ] Terminal's `===== GMAIL SEND ERROR =====` block checked for the
      real Gmail API error message

</details>

<details>
<summary><b>📖 Using the app</b></summary>

1. **Paste addresses or upload a CSV.** Headers are matched
   case-insensitively: `Email`, `Name`, `Company`, `Position`, `Gender`
   (also accepts `Company Contact Name`). Invalid and duplicate rows are
   flagged and skipped automatically.
2. **Write your letter once.** Use `{{name}}`, `{{company}}`,
   `{{position}}` anywhere in the subject or body. Don't type the
   greeting yourself — it's added automatically above your message based
   on each recipient's data.
3. **Upload your resume** (attached to every email) and any optional
   extra attachments (cover letter, certificates, portfolio).
4. **Preview & edit before sending** — step through each recipient's
   exact email, including the resolved greeting, and tweak anything
   before it goes out.
5. **Set a delay**, hit **Send**, and watch progress live. Retry any
   failures with one click once the batch finishes.
6. Check **Send history** any time — search it or export it as a CSV
   report.

#### Greeting system

The app does not guess a recipient's gender from an email address. When
your CSV gives high-confidence evidence — an explicit `Gender` column, or
a `Company Contact Name` with an honorific like `Mr.`/`Ms.` — that's used
directly. A small name-based heuristic is used only at medium-or-higher
confidence. Anything less certain falls back to `Dear Hiring Manager,` or
`Dear Recruitment Team,` rather than risking a wrong guess. You can see
and override the resolved greeting for every recipient in the preview
step.

</details>

<details>
<summary><b>🗂️ Project structure</b></summary>

```
app/
  api/
    auth/[...nextauth]/route.ts   # Google OAuth via NextAuth
    send/route.ts                 # Sends one email via the Gmail API
  page.tsx                        # Landing / dashboard switch
  layout.tsx, providers.tsx, globals.css
components/
  TopBar, SignInGate, Dashboard
  RecipientsUploader, RecipientsTable
  TemplateEditor, TemplateManager
  AttachmentUploader, PreviewModal
  SendPanel, HistoryPanel
lib/
  auth.ts       # NextAuth config + token refresh
  mime.ts       # RFC 2822 MIME message builder (with attachments)
  gender.ts     # Greeting/gender-inference heuristic
  csv.ts        # CSV/plain-text parsing, validation, {{variables}}
  jobs.ts       # Builds per-recipient send jobs from a template
  store.ts      # Zustand store (templates, history, settings) → localStorage
  file.ts       # File → base64 helper for attachments
types/index.ts  # Shared TypeScript types
```

#### How it works

```
User → Google OAuth → NextAuth Session → Recipient List / CSV
     → Email Template → Personalized Email → Preview
     → Resume / Attachments → Gmail API → Recipient
```

</details>

<details>
<summary><b>🚀 Deployment (Vercel or any Node host)</b></summary>

This project's backend is just Next.js API routes, so it deploys as a
single app on Vercel — no separate backend service needed.

```bash
npm install -g vercel
vercel
```

1. In the Vercel dashboard, add the same four environment variables from
   `.env`, with `NEXTAUTH_URL` set to your real Vercel domain.
2. Add `https://<your-vercel-domain>/api/auth/callback/google` to
   **Authorized redirect URIs** in your Google OAuth client.
3. Redeploy after adding env vars so they take effect.

Any other Node.js host that supports Next.js API routes (Render,
Railway, a VM running `next start`, etc.) works the same way — same four
env vars, matching callback URL registered with Google.

</details>

<details>
<summary><b>🔒 Security notes</b></summary>

- The app requests only `gmail.send`, plus the standard `openid`,
  `email`, and `profile` scopes needed for sign-in itself — it cannot
  read, delete, or search your mail, and cannot see your other Google
  data beyond your basic profile/email used to identify your account.
- OAuth access/refresh tokens are held server-side in an encrypted
  NextAuth JWT session cookie, not in browser-accessible storage.
- Resume/attachment bytes and your recipient list are processed in your
  browser and sent directly to your own deployment's `/api/send` route —
  they aren't stored in any third-party service by this app.
- Templates and send history persist in `localStorage` on your device
  only.
- Never commit `.env` to version control — `.gitignore` already excludes
  it. Before pushing, double check with `git status` that `.env` isn't
  listed. If `GOOGLE_CLIENT_SECRET` or `NEXTAUTH_SECRET` are ever
  accidentally pushed, rotate them immediately in Google Cloud Console.

</details>

<details>
<summary><b>⚠️ Known limitations</b></summary>

- Gmail doesn't expose an API for "sends remaining today" — the daily
  counter is tracked locally in your browser and resets if you clear
  site data or switch devices/browsers.
- Scheduled/future-dated sending isn't implemented; sends happen
  immediately when you click Send.
- History and templates are per-browser (`localStorage`). Swap the
  Zustand store's persistence for a real database (SQLite/Postgres) if
  you need them synced across devices.
- Gender/greeting inference is a best-effort heuristic by design — see
  [Greeting system](#greeting-system) above.

</details>

---

<div align="center">

**Tech:** Python · Azure OpenAI · python-telegram-bot · SQLite · Next.js · React · TypeScript · Tailwind CSS · NextAuth.js · Gmail API · Zustand

<sub>MIT licensed · built for personal job-application automation · a real employer never asks you to pay to apply</sub>

</div>
