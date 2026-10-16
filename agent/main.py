"""Job-hunt agent: searches on a timer, asks you on Telegram before every email.

  python main.py            run the bot + scheduler (what the server runs)
  python main.py --whoami   print your Telegram chat id (message your bot first)
  python main.py --dry-run  one search cycle, print drafts, send nothing
"""
import asyncio
import html
import json
import logging
import sys
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from jobagent import db
from jobagent.config import CFG, env
from jobagent.mailer import send_email
from jobagent.pipeline import redraft, run_cycle

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("main")

CHAT_ID = int(env("TELEGRAM_CHAT_ID") or 0)
SEND = CFG["sending"]
send_lock = asyncio.Lock()
cycle_lock = asyncio.Lock()


# ---------- cards ----------

def card_text(lead, status_line=""):
    e = html.escape
    reason = (f"🟢 <b>Hiring:</b> {e(lead['hiring_role'])}" if lead.get("hiring_role")
              else "🔵 <b>AI company</b> (no posted opening — writing to HR)")
    lines = [
        f"<b>{e(lead['company'])}</b> · {e(lead.get('city') or '')}",
        reason,
        f"🏢 {e(lead.get('what_they_do') or '')}",
        f"💡 {e(lead.get('why') or '')}",
        f"🌐 {e(lead['website'])}" + (f" · <a href=\"{e(lead['job_url'])}\">job post</a>" if lead.get("job_url") else ""),
        f"✉️ <b>To:</b> {e(lead['email'])}",
        (f"   found on: {e(lead['email_source'])}" if lead.get("email_source")
         else "   ⚠️ typed by you / not verified on the website"),
    ]
    others = [x for x in json.loads(lead.get("all_emails") or "[]") if x != lead["email"]][:3]
    if others:
        lines.append(f"   other addresses: {e(', '.join(others))}")
    lines += ["", f"<b>Subject:</b> {e(lead['subject'])}", "", e(lead["body"])]
    if status_line:
        lines += ["", status_line]
    return "\n".join(lines)[:4000]


def buttons(lead_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Send", callback_data=f"send:{lead_id}"),
         InlineKeyboardButton("🔁 Rewrite", callback_data=f"regen:{lead_id}"),
         InlineKeyboardButton("❌ Skip", callback_data=f"skip:{lead_id}")],
    ])


async def post_card(bot, lead):
    msg = await bot.send_message(CHAT_ID, card_text(lead), parse_mode="HTML", reply_markup=buttons(lead["id"]),
                                 disable_web_page_preview=True)
    db.kv_set(f"msg:{msg.message_id}", lead["id"])


# ---------- sending ----------

async def do_send(lead_id):
    """Returns a status line for the card."""
    lead = db.get_lead(lead_id)
    if lead["status"] == "sent":
        return "Already sent."
    if db.sent_today() >= SEND["daily_limit"]:
        return f"⏸ Daily limit ({SEND['daily_limit']}) reached. Tap Send again tomorrow."
    async with send_lock:
        wait = float(db.kv_get("last_send_ts", 0)) + SEND["min_gap_seconds"] - time.time()
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            await asyncio.to_thread(send_email, lead["email"], lead["subject"], lead["body"])
        except Exception as e:
            db.update_lead(lead_id, status="failed", error=str(e))
            return f"⚠️ Send failed: {html.escape(str(e))[:300]}"
        db.kv_set("last_send_ts", time.time())
    db.update_lead(lead_id, status="sent", sent_at=db.now())
    return f"✅ Sent to {html.escape(lead['email'])} ({db.sent_today()}/{SEND['daily_limit']} today)"


# ---------- scheduled cycle ----------

async def cycle(context: ContextTypes.DEFAULT_TYPE):
    if db.kv_get("paused") == "1" or cycle_lock.locked():
        return
    async with cycle_lock:
        try:
            ids = await asyncio.to_thread(run_cycle)
        except Exception:
            log.exception("cycle failed")
            await context.bot.send_message(CHAT_ID, "⚠️ Search cycle crashed — check the server logs.")
            return
    for lead_id in ids:
        lead = db.get_lead(lead_id)
        if SEND["auto_send"]:
            status = await do_send(lead_id)
            await context.bot.send_message(CHAT_ID, card_text(db.get_lead(lead_id), status), parse_mode="HTML",
                                           disable_web_page_preview=True)
        else:
            await post_card(context.bot, lead)
    log.info("cycle done: %d new drafts", len(ids))


# ---------- handlers ----------

def mine(update: Update):
    return update.effective_chat and update.effective_chat.id == CHAT_ID


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not mine(update):
        return await q.answer()
    action, lead_id = q.data.split(":")
    lead_id = int(lead_id)
    lead = db.get_lead(lead_id)
    if action == "send":
        await q.answer("Sending…")
        status = await do_send(lead_id)
        done = db.get_lead(lead_id)["status"] == "sent"
        await q.edit_message_text(card_text(db.get_lead(lead_id), status), parse_mode="HTML",
                                  disable_web_page_preview=True, reply_markup=None if done else buttons(lead_id))
    elif action == "skip":
        db.update_lead(lead_id, status="skipped")
        await q.answer("Skipped")
        await q.edit_message_text(card_text(lead, "❌ Skipped"), parse_mode="HTML", disable_web_page_preview=True)
    elif action == "regen":
        await q.answer("Rewriting…")
        lead = await asyncio.to_thread(redraft, lead_id)
        await q.edit_message_text(card_text(lead, "🔁 Rewritten"), parse_mode="HTML",
                                  disable_web_page_preview=True, reply_markup=buttons(lead_id))


async def on_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a card: 'to: x@y.com' changes the recipient, any other text is a rewrite instruction."""
    if not mine(update) or not update.message.reply_to_message:
        return
    lead_id = db.kv_get(f"msg:{update.message.reply_to_message.message_id}")
    if not lead_id:
        return
    lead_id, text = int(lead_id), update.message.text.strip()
    if text.lower().startswith("to:"):
        db.update_lead(lead_id, email=text[3:].strip(), email_source=None)
        lead = db.get_lead(lead_id)
    else:
        lead = await asyncio.to_thread(redraft, lead_id, text)
    await post_card(context.bot, lead)


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if mine(update):
        await update.message.reply_text("🔎 Searching now…")
        await cycle(context)
        await update.message.reply_text("Done.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if mine(update):
        s = db.stats()
        await update.message.reply_text(
            ("\n".join(f"{k}: {v}" for k, v in sorted(s.items())) or "Nothing yet.")
            + f"\n\nSent today: {db.sent_today()}/{SEND['daily_limit']}"
            + ("\n⏸ paused" if db.kv_get("paused") == "1" else ""))


async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if mine(update):
        leads = db.leads_with_status("pending")
        for lead in leads[:15]:
            await post_card(context.bot, lead)
        if not leads:
            await update.message.reply_text("No drafts waiting.")


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if mine(update):
        db.kv_set("paused", "1")
        await update.message.reply_text("⏸ Paused. /resume to continue.")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if mine(update):
        db.kv_set("paused", "0")
        await update.message.reply_text("▶️ Resumed.")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Your chat id is {update.effective_chat.id}.\n\n"
        "/run – search now\n/pending – show drafts waiting\n/stats – counts\n/pause, /resume\n\n"
        "Reply to a draft with text to rewrite it that way, or with 'to: someone@company.com' to change recipient.")


# ---------- entry points ----------

def whoami():
    import httpx
    r = httpx.get(f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/getUpdates", timeout=20).json()
    chats = {u["message"]["chat"]["id"]: u["message"]["chat"].get("first_name") for u in r.get("result", [])
             if "message" in u}
    print(chats or "No messages yet — send /start to your bot in Telegram, then run this again.")


def dry_run():
    for lead_id in run_cycle():
        lead = db.get_lead(lead_id)
        print("=" * 70, f"\n{lead['company']} | {lead['city']} | {lead['email']} | role: {lead['hiring_role']}")
        print(f"Subject: {lead['subject']}\n\n{lead['body']}\n")
    print("stats:", db.stats())


def main():
    if not (env("TELEGRAM_BOT_TOKEN") and CHAT_ID):
        sys.exit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env (see .env.example).")
    app = Application.builder().token(env("TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY & ~filters.COMMAND, on_reply))
    app.job_queue.run_repeating(cycle, interval=CFG["search"]["every_hours"] * 3600, first=30)
    log.info("agent started; searching every %sh", CFG["search"]["every_hours"])
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    if "--whoami" in sys.argv:
        whoami()
    elif "--dry-run" in sys.argv:
        dry_run()
    else:
        main()
