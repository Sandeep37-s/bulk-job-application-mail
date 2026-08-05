import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { google } from "googleapis";
import { authOptions } from "@/lib/auth";
import { buildRawMimeMessage, type MimeAttachment } from "@/lib/mime";

export const runtime = "nodejs";

interface SendRequestBody {
  to: string;
  subject: string;
  body: string;
  attachments: MimeAttachment[];
}

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  const accessToken = (session as any)?.accessToken;

  if (!session || !accessToken) {
    return NextResponse.json(
      { error: "Not authenticated. Please sign in with Google again." },
      { status: 401 }
    );
  }
  if ((session as any).error === "RefreshAccessTokenError") {
    return NextResponse.json(
      { error: "Your Google session expired. Please sign in again." },
      { status: 401 }
    );
  }

  let payload: SendRequestBody;
  try {
    payload = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body." }, { status: 400 });
  }

  const { to, subject, body, attachments } = payload;

  if (!to || !subject || !body) {
    return NextResponse.json(
      { error: "Missing required fields: to, subject, body." },
      { status: 400 }
    );
  }

  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRe.test(to)) {
    return NextResponse.json({ error: `Invalid recipient address: ${to}` }, { status: 400 });
  }

  try {
    const oauth2Client = new google.auth.OAuth2();
    oauth2Client.setCredentials({ access_token: accessToken });
    const gmail = google.gmail({ version: "v1", auth: oauth2Client });

    const fromEmail = session.user?.email ?? "me";

    const raw = buildRawMimeMessage({
      from: fromEmail,
      to,
      subject,
      bodyText: body,
      attachments: attachments ?? [],
    });

    const result = await gmail.users.messages.send({
      userId: "me",
      requestBody: { raw },
    });

    return NextResponse.json({ success: true, messageId: result.data.id });
  }catch (error: any) {
  console.error("===== GMAIL SEND ERROR =====");
  console.error(error);
  console.error(error.response?.data);
  console.error("============================");

  const message =
    error?.errors?.[0]?.message ||
    error?.response?.data?.error?.message ||
    error?.message ||
    "Unknown error while sending email.";

  return NextResponse.json({ error: message }, { status: 500 });
}
}