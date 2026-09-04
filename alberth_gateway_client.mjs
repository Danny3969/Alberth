import { c as callGateway } from "/usr/local/lib/node_modules/openclaw/dist/call-BlqKbSL2.js";
import { randomUUID } from "node:crypto";

const message = process.argv[2];
const agent = process.argv[3] || "main";
const sessionId = process.argv[4] || "sesion-web-alberth";

if (!message) {
  console.error("Error: Mensaje requerido");
  process.exit(1);
}

try {
  const response = await callGateway({
    method: "agent",
    params: {
      message: message,
      agentId: agent,
      idempotencyKey: randomUUID(),
      sessionId: sessionId,
      deliver: false
    },
    expectFinal: true,
    timeoutMs: 90000
  });

  const reply = response?.result?.payloads?.[0]?.text || "Entendido.";
  console.log(reply);
  process.exit(0);
} catch (err) {
  console.error("Error:", err.message);
  process.exit(1);
}
