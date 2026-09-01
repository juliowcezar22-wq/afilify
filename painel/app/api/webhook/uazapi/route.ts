import { NextRequest, NextResponse } from "next/server";
import { executar } from "@/lib/dados";

/* Recebe os avisos da uazapi em tempo real e guarda na tabela
   rival_mensagens. O worker consome de lá.  // harness-ok (comentário de código)

   Público por necessidade (a uazapi precisa alcançar), então a chave  // harness-ok
   secreta é obrigatória: sem ela, qualquer um poderia fazer o grupo
   publicar o link que quisesse.

   Responde rápido e sempre 200 nos casos normais — webhook que demora
   ou devolve erro faz o remetente reenviar e acumular fila do lado dele. */

function primeiro(...valores: unknown[]): string {
  for (const v of valores) {
    if (typeof v === "string" && v.trim()) return v.trim();
    if (typeof v === "number" && v) return String(v);
  }
  return "";
}

function extrair(corpo: Record<string, unknown>) {
  // a uazapi varia o envelope conforme o evento; tentamos os formatos
  // conhecidos sem inventar: pegamos o primeiro que tiver id de mensagem
  const cands = [corpo, corpo.message, corpo.data, (corpo.data as never)?.["message"]]
    .filter((x): x is Record<string, unknown> => !!x && typeof x === "object");
  for (const c of cands) {
    const chave = (c.key ?? {}) as Record<string, unknown>;
    const messageid = primeiro(c.messageid, c.id, chave.id);
    const chatid = primeiro(c.chatid, c.chat, c.remoteJid, chave.remoteJid);
    if (messageid && chatid) {
      return {
        messageid, chatid,
        texto: primeiro(c.text, c.body, c.caption, c.conversation),
        tipo: primeiro(c.messageType, c.type, c.messagetype),
        de_mim: c.fromMe === true || chave.fromMe === true ? 1 : 0,
        ts: primeiro(c.messageTimestamp, c.timestamp, c.t),
      };
    }
  }
  return null;
}

export async function POST(req: NextRequest) {
  const esperado = process.env.WEBHOOK_SECRET ?? "";
  const veio = req.nextUrl.searchParams.get("token")
    ?? req.headers.get("x-webhook-token") ?? "";
  if (!esperado || veio !== esperado) {
    return NextResponse.json({ erro: "token" }, { status: 401 });
  }

  let corpo: Record<string, unknown>;
  try {
    corpo = await req.json();
  } catch {
    return NextResponse.json({ ok: true, ignorado: "corpo ilegível" });
  }

  const m = extrair(corpo);
  if (!m) return NextResponse.json({ ok: true, ignorado: "sem mensagem" });
  if (!m.chatid.endsWith("@g.us")) {
    return NextResponse.json({ ok: true, ignorado: "não é grupo" });
  }
  if (m.de_mim) return NextResponse.json({ ok: true, ignorado: "minha própria" });

  try {
    await executar(
      `INSERT INTO rival_mensagens
         (messageid, chatid, texto, tipo, de_mim, ts_mensagem, recebido_em, processado, bruto)
       VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
       ON CONFLICT (messageid) DO NOTHING`,
      [m.messageid, m.chatid, m.texto, m.tipo, m.de_mim, m.ts,
       new Date().toISOString(), JSON.stringify(corpo).slice(0, 4000)],
    );
  } catch (e) {
    // nunca devolver erro para a uazapi por falha nossa de banco: ela
    // reenviaria em loop. O histórico (rede de segurança) cobre isso.
    console.error("webhook: falha ao gravar", e);
    return NextResponse.json({ ok: true, gravado: false });
  }
  return NextResponse.json({ ok: true, gravado: true });
}

export async function GET() {
  return NextResponse.json({ ok: true, servico: "webhook uazapi" }); // harness-ok (resposta técnica, não tela)
}
