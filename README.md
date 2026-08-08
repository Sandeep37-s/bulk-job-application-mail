# Dispatch — Bulk Job-Application Email Sender

Send personalized job-application emails to many recruiters, one click at a
time, directly from your own Gmail account.

Built with **Next.js, React, TypeScript, Tailwind CSS, NextAuth.js, and the
Gmail API**.

---

## Features

- Google OAuth 2.0 authentication
- Uses the Gmail API with the `gmail.send` scope
- Sends emails directly from the user's Gmail account
- Paste multiple email addresses at once
- Import recipients using CSV
- Personalized email templates
- Supports `{{name}}`, `{{company}}`, and `{{position}}` placeholders
- Automatic, conservative greeting handling
- Resume and additional file attachments
- Live email preview before sending, editable per recipient
- Configurable delay between emails
- Duplicate email detection and address validation
- Send history with search
- Failed-email retry
- CSV export of send history
- Daily sending counter with limit warning
- Local browser storage using `localStorage`
- No database required for local usage

---

## Google Cloud setup (OAuth + Gmail API)

The application uses **Google OAuth 2.0** and the **Gmail API** to send
emails through the user's Gmail account. You must configure Google Cloud
before running the app — this takes about five minutes.

### 1. Create a Google Cloud project

Open [console.cloud.google.com](https://console.cloud.google.com/) and
create a new project, e.g. `Dispatch Email Sender`. Make sure the new
project is selected before continuing.

### 2. Enable the Gmail API

**Google Cloud Console → APIs & Services → Library** → search `Gmail API`
→ **Enable**. If it already says "Manage" instead of "Enable", it's
already on.

### 3. Configure the OAuth consent screen

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

### 4. Create an OAuth Client ID

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

---

## Environment variables

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

---

## Installation

```bash
cd bulk-email-sender
npm install
npm run dev
```

Open `http://localhost:3000`, click **Sign in with Google**, and sign in
with the account you added as a **Test user**. Accept the "Send email on
your behalf" permission when prompted.

---

## OAuth troubleshooting

These are the actual errors you're likely to hit and how to fix each one.

### `Error 400: redirect_uri_mismatch`

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

### `Error 403: access_denied`

**Cause:** the Google account you're signing in with isn't registered as
a test user while the app is in Testing mode.

**Fix:** Google Auth Platform → Audience → Test users → add that Gmail
address → sign in again.

### `Request had insufficient authentication scopes` / `Insufficient Permission` (Gmail API 403)

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

### Debugging `/api/send` 500s in general

A bare `POST /api/send 500` in your terminal doesn't show *why* Gmail
rejected the request. `app/api/send/route.ts` logs the full Gmail API
error to the server console specifically so you can see the real reason
— look for the block between `===== GMAIL SEND ERROR =====` and `====`
in your terminal output, and check the `error.response.data.error`
field for Gmail's actual message (e.g. `insufficientPermissions`,
`invalid_grant`, rate-limit errors, etc.).

---

## Troubleshooting checklist

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

---

## Using the app

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

### Greeting system

The app does not guess a recipient's gender from an email address. When
your CSV gives high-confidence evidence — an explicit `Gender` column, or
a `Company Contact Name` with an honorific like `Mr.`/`Ms.` — that's used
directly. A small name-based heuristic is used only at medium-or-higher
confidence. Anything less certain falls back to `Dear Hiring Manager,` or
`Dear Recruitment Team,` rather than risking a wrong guess. You can see
and override the resolved greeting for every recipient in the preview
step.

---

## Project structure

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

### How it works

```
User → Google OAuth → NextAuth Session → Recipient List / CSV
     → Email Template → Personalized Email → Preview
     → Resume / Attachments → Gmail API → Recipient
```

---

## Deployment

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

---

## Security notes

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

---

## Known limitations

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

---

## Technologies used

Next.js · React · TypeScript · Tailwind CSS · NextAuth.js ·
Google OAuth 2.0 · Gmail API · Zustand · Node.js · Vercel

---

## License

This project is intended for educational and personal job-application
automation purposes.
