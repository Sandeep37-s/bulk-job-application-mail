export interface MimeAttachment {
  filename: string;
  mimeType: string;
  base64: string; // raw base64, no data: prefix
}

export interface BuildMimeOptions {
  from: string;
  to: string;
  subject: string;
  bodyText: string;
  attachments: MimeAttachment[];
}

function encodeSubject(subject: string): string {
  // RFC 2047 encoding so non-ASCII subjects survive transport
  return `=?UTF-8?B?${Buffer.from(subject, "utf-8").toString("base64")}?=`;
}

/** Build a raw RFC 2822 MIME message (multipart/mixed) and base64url-encode it for Gmail's `raw` field. */
export function buildRawMimeMessage(opts: BuildMimeOptions): string {
  const boundaryMixed = `mixed_${Date.now()}_${Math.random().toString(36).slice(2)}`;

  const headers = [
    `From: ${opts.from}`,
    `To: ${opts.to}`,
    `Subject: ${encodeSubject(opts.subject)}`,
    `MIME-Version: 1.0`,
    `Content-Type: multipart/mixed; boundary="${boundaryMixed}"`,
  ].join("\r\n");

  const textPart = [
    `--${boundaryMixed}`,
    `Content-Type: text/plain; charset="UTF-8"`,
    `Content-Transfer-Encoding: 7bit`,
    ``,
    opts.bodyText,
    ``,
  ].join("\r\n");

  const attachmentParts = opts.attachments
    .map((att) => {
      return [
        `--${boundaryMixed}`,
        `Content-Type: ${att.mimeType}; name="${att.filename}"`,
        `Content-Disposition: attachment; filename="${att.filename}"`,
        `Content-Transfer-Encoding: base64`,
        ``,
        chunkBase64(att.base64),
        ``,
      ].join("\r\n");
    })
    .join("");

  const closing = `--${boundaryMixed}--`;

  const raw = `${headers}\r\n\r\n${textPart}${attachmentParts}${closing}`;

  return Buffer.from(raw, "utf-8")
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function chunkBase64(base64: string): string {
  // RFC requires base64 body lines to be wrapped, conventionally at 76 chars.
  const chunks: string[] = [];
  for (let i = 0; i < base64.length; i += 76) {
    chunks.push(base64.slice(i, i + 76));
  }
  return chunks.join("\r\n");
}
