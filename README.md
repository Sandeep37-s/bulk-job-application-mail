# Dispatch — Bulk Job-Application Email Sender

Send personalized job-application emails to many recruiters, one click at a
time, straight from **your own Gmail account**. Built with Next.js, React,
TypeScript, Tailwind CSS, and the Gmail API.

---

## What it does

- Signs you in with **Google OAuth 2.0** (`gmail.send` scope only — the app
  can send mail on your behalf but can never read your inbox).
- Accepts a **pasted list of emails** or a **CSV** with `Email, Name,
  Company, Position, Gender` columns.
- Writes **one template** with `{{name}}`, `{{company}}`, `{{position}}`
  placeholders, and saves unlimited named templates for reuse.
- Chooses a greeting per recipient — `Dear Sir,` / `Dear Madam,` only when
  your data gives high-confidence evidence (an explicit `Gender` column or a
  contact name with an honorific). Otherwise it always falls back to `Dear
  Hiring Manager,` / `Dear Recruitment Team,` rather than guessing. See
  [A note on the greeting detection](#a-note-on-the-greeting-detection) below.
- Attaches your resume (and any extra files — cover letter, certificates,
  portfolio) to every email.
- Shows a **live preview** of exactly what each recipient will receive, with
  the subject, body, and greeting editable before you send.
- Sends with a configurable **delay** (2/5/10s) between messages, tracks
  **today's sent count** against a daily limit, and warns before you'd go
  over it.
- Tracks **send history** (searchable, exportable as CSV) and lets you
  **retry failed sends** with one click.
- Validates addresses, removes duplicates, and skips empty rows before
  anything is sent.

Everything except the OAuth token and the Gmail API call itself runs and
stores data in your browser (`localStorage`) — there's no database to set
up, though you can add one later if you want server-side history.

---

## 1. Google Cloud setup (OAuth + Gmail API)

You need a Google Cloud project with the Gmail API enabled and an OAuth
Client ID. This takes about five minutes.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and
   create a new project (or pick an existing one).
2. **Enable the Gmail API**: *APIs & Services → Library* → search "Gmail
   API" → **Enable**.
3. **Configure the OAuth consent screen**: *APIs & Services → OAuth consent
   screen*.
   - User type: "External" is fine for personal use (you'll add yourself as
     a test user).
   - Add the scope `https://www.googleapis.com/auth/gmail.send`.
   - Add your Google account under **Test users** (required while the app
     is in "Testing" publishing status — otherwise Google blocks sign-in).
4. **Create credentials**: *APIs & Services → Credentials → Create
   Credentials → OAuth client ID*.
   - Application type: **Web application**.
   - Authorized redirect URIs:
     - `http://localhost:3000/api/auth/callback/google` (local dev)
     - `https://your-deployed-domain.com/api/auth/callback/google`
       (production — add this once you know your deployed URL)
5. Copy the generated **Client ID** and **Client Secret**.

> **Note on verification:** while your OAuth consent screen is in
> "Testing" mode, only accounts you've explicitly added as test users can
> sign in, and Google shows an "unverified app" warning that you can click
> through. That's expected and fine for personal use. If you want to remove
> the warning for other users, you'd need to submit the app for Google's
> verification review — not required to use this yourself.

---

## 2. Local setup

```bash
# 1. Install dependencies
npm install

# 2. Copy the env file and fill in your values
cp .env.example .env

# 3. Generate a NextAuth secret
openssl rand -base64 32
# paste the output into NEXTAUTH_SECRET in .env

# 4. Run the dev server
npm run dev
```

Open `http://localhost:3000`, click **Sign in with Google**, and grant the
Gmail send permission.

### `.env` reference

| Variable               | Where to get it                                      |
|-------------------------|-------------------------------------------------------|
| `GOOGLE_CLIENT_ID`      | Google Cloud Console → Credentials                    |
| `GOOGLE_CLIENT_SECRET`  | Google Cloud Console → Credentials                    |
| `NEXTAUTH_SECRET`       | `openssl rand -base64 32`                             |
| `NEXTAUTH_URL`          | `http://localhost:3000` locally, your real domain in prod |

---

## 3. Using the app

1. **Paste addresses or upload a CSV.** CSV headers are matched
   case-insensitively: `Email`, `Name`, `Company`, `Position`, `Gender`
   (also accepts `Company Contact Name`). Invalid and duplicate rows are
   flagged and skipped automatically.
2. **Write your letter once.** Use `{{name}}`, `{{company}}`, `{{position}}`
   anywhere in the subject or body — they're filled in per recipient. Don't
   include the greeting line yourself; it's added automatically above your
   message.
3. **Upload your resume** (attached to every email) and any optional extra
   attachments.
4. **Preview & edit before sending** — step through each recipient's exact
   email, including the resolved greeting, and tweak anything before it
   goes out.
5. **Set a delay** and hit **Send**. Watch progress live; failed sends can
   be retried with one click once the batch finishes.
6. Check **Send history** any time, search it, or export it as a CSV
   report.

### A note on the greeting detection

There is no reliable way to determine someone's gender from an email
address or a bare first name — names are shared across genders and
cultures. This app treats that as a hard rule, not a suggestion:

- If your CSV has an explicit `Gender` column, or a `Company Contact Name`
  with an honorific (`Mr.`, `Ms.`, etc.), that's used directly.
- Otherwise, a first-name match against a small, high-confidence list is
  used **only** at medium-or-higher confidence.
- **Anything less certain always falls back to `Dear Hiring Manager,` or
  `Dear Recruitment Team,`.** It will never guess `Sir`/`Madam` from an
  email address alone, and you can see and override the resolved greeting
  for every recipient in the preview step.

---

## 4. Deployment

### Frontend + API routes → Vercel

This project's backend is just Next.js API routes, so it deploys as a
single app — no separate backend service needed.

```bash
npm install -g vercel
vercel
```

1. In the Vercel dashboard, add the same environment variables from
   `.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `NEXTAUTH_SECRET`,
   and `NEXTAUTH_URL` set to your Vercel URL).
2. Add `https://<your-vercel-domain>/api/auth/callback/google` to the
   **Authorized redirect URIs** in your Google OAuth client (step 4 above).
3. Redeploy after adding env vars so they take effect.

### Alternative hosts

Any Node.js host that supports Next.js API routes works the same way
(Render, Railway, a VM with `next start`, etc.) — just set the same four
environment variables and register the matching callback URL with Google.

---

## 5. Project structure

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
  gender.ts     # Greeting/gender-inference heuristic (see note above)
  csv.ts        # CSV/plain-text parsing, validation, {{variables}}
  jobs.ts       # Builds per-recipient send jobs from a template
  store.ts      # Zustand store (templates, history, settings) → localStorage
  file.ts       # File → base64 helper for attachments
types/index.ts  # Shared TypeScript types
```

---

## 6. Security notes

- The Gmail OAuth scope requested is `gmail.send` only — this app cannot
  read, delete, or search your mail, and cannot see your other Google data.
- Your OAuth access/refresh tokens are held server-side in an encrypted
  NextAuth JWT session cookie; they are never sent to or stored in the
  browser's JavaScript-accessible storage.
- Resume/attachment bytes and your recipient list are processed in your
  browser and sent directly to the `/api/send` route on your own deployment
  — they aren't stored in any third-party service by this app.
- Templates and send history persist in `localStorage` on your device only.
- Keep `GOOGLE_CLIENT_SECRET` and `NEXTAUTH_SECRET` out of version control
  (already covered by `.gitignore`).

## 7. Known limitations / good next steps

- Gmail doesn't expose an API for "sends remaining today" — the daily
  counter is tracked locally in your browser, so it resets if you clear
  site data or switch devices/browsers.
- Scheduled/future-dated sending isn't implemented; sends happen
  immediately when you click Send.
- History and templates are per-browser (`localStorage`). Swap the Zustand
  store's persistence for a real database (SQLite/Postgres) if you need
  them synced across devices.
- Gender/greeting inference is a best-effort heuristic by design — see
  [above](#a-note-on-the-greeting-detection).
"# bulk-job-application-mail" 
