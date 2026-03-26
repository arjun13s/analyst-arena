import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { motion } from "motion/react";
import confetti from "canvas-confetti";
import { MatchResultPayload } from "./api";

function OpenAILogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z" />
    </svg>
  );
}

export function WinnerAnnouncement() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [result, setResult] = useState<MatchResultPayload | null>(null);
  const [showLog, setShowLog] = useState(false);
  const confettiDone = useRef(false);
  const matchId = searchParams.get("matchId") || "";

  useEffect(() => {
    if (!matchId) return;
    const raw = sessionStorage.getItem(`match:${matchId}`);
    if (!raw) return;
    try {
      setResult(JSON.parse(raw) as MatchResultPayload);
    } catch {
      setResult(null);
    }
  }, [matchId]);

  // Must run on every render (same order as other hooks); cannot sit after `if (!result) return`.
  useEffect(() => {
    if (!result) return;
    if (confettiDone.current) return;
    confettiDone.current = true;
    const isHudWinner = result.winner === "hud_model";
    const colors = isHudWinner ? ["#FFB800", "#00DD77", "#ffffff"] : ["#10A37F", "#00DD77", "#ffffff"];
    const end = Date.now() + 2500;
    const fire = () => {
      confetti({ particleCount: 3, angle: 60, spread: 55, origin: { x: 0 }, colors });
      confetti({ particleCount: 3, angle: 120, spread: 55, origin: { x: 1 }, colors });
      if (Date.now() < end) requestAnimationFrame(fire);
    };
    fire();
  }, [result]);

  if (!result) return <div className="min-h-screen w-full flex items-center justify-center text-[#8888AA]">No winner data found.</div>;

  const isHudWinner = result.winner === "hud_model";
  const winnerAccent = isHudWinner ? "#FFB800" : "#10A37F";
  const hudVal = result.agent_a.final_portfolio_value;
  const oaiVal = result.agent_b.final_portfolio_value;
  const hudTrades = result.agent_a.trade_count;
  const oaiTrades = result.agent_b.trade_count;
  const hudReturn = result.agent_a.total_return_pct.toFixed(2);
  const oaiReturn = result.agent_b.total_return_pct.toFixed(2);
  const hudDrawdown = result.agent_a.max_drawdown_pct.toFixed(1);
  const oaiDrawdown = result.agent_b.max_drawdown_pct.toFixed(1);
  const winnerVal = isHudWinner ? hudVal : oaiVal;
  const loserVal = isHudWinner ? oaiVal : hudVal;

  const fmt = (v: number) => "$" + v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const stats = [
    { label: "Final Value", hud: fmt(hudVal), oai: fmt(oaiVal) },
    { label: "Total Return", hud: `${Number(hudReturn) >= 0 ? "+" : ""}${hudReturn}%`, oai: `${Number(oaiReturn) >= 0 ? "+" : ""}${oaiReturn}%` },
    { label: "Total Trades", hud: String(hudTrades), oai: String(oaiTrades) },
    { label: "Max Drawdown", hud: `${hudDrawdown}%`, oai: `${oaiDrawdown}%` },
  ];

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center relative overflow-hidden" style={{ background: "radial-gradient(ellipse at center, #1a1a2e 0%, #0A0A0F 70%)", fontFamily: "Inter, sans-serif" }}>
      <div className="absolute w-[400px] h-[400px] rounded-full blur-[120px] opacity-20" style={{ background: winnerAccent, top: "15%", left: "50%", transform: "translateX(-50%)" }} />

      <motion.div initial={{ opacity: 0, scale: 0.5 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8, type: "spring" }} className="relative z-10 flex flex-col items-center">
        <div className="w-32 h-32 rounded-2xl flex items-center justify-center mb-6" style={{ background: "#14141F", border: `2px solid ${winnerAccent}`, boxShadow: `0 0 60px ${winnerAccent}40, 0 0 120px ${winnerAccent}20` }}>
          {isHudWinner ? (
            <div className="bg-white rounded-lg px-3 py-2">
              <img src="/hud-logo.png" alt="HUD logo" className="h-10 object-contain" />
            </div>
          ) : (
            <OpenAILogo className="h-14 w-14 text-white" />
          )}
        </div>
        <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="text-white mb-1" style={{ fontFamily: "'Playfair Display', serif", fontWeight: 900, fontSize: "20px", color: "#8888AA" }}>
          {isHudWinner ? result.agent_a.display_name : result.agent_b.display_name}
        </motion.h1>
        <motion.h2 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }} style={{ fontFamily: "'Playfair Display', serif", fontWeight: 900, fontSize: "72px", color: winnerAccent, textShadow: `0 0 40px ${winnerAccent}60` }}>
          WINS
        </motion.h2>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }} className="text-center">
          <div className="text-white mb-1" style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: "36px", textShadow: `0 0 20px ${winnerAccent}40` }}>{fmt(winnerVal)}</div>
          <div className="text-[#8888AA]" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "14px" }}>vs {fmt(loserVal)}</div>
        </motion.div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1 }} className="mt-10 w-full max-w-2xl rounded-xl p-6 relative z-10" style={{ background: "#14141F", border: "1px solid #1E1E2E" }}>
        <div className="grid grid-cols-3 gap-4 text-center mb-3"><div className="text-sm" style={{ color: "#FFB800", fontFamily: "'JetBrains Mono', monospace" }}>hud</div><div /><div className="text-sm" style={{ color: "#10A37F", fontFamily: "'JetBrains Mono', monospace" }}>ChatGPT</div></div>
        {stats.map((s) => (
          <div key={s.label} className="grid grid-cols-3 gap-4 text-center py-2 border-t border-[#1E1E2E]">
            <div className="text-sm" style={{ fontFamily: "'JetBrains Mono', monospace", color: isHudWinner ? "#ffffff" : "#8888AA" }}>{s.hud}</div>
            <div className="text-[#8888AA] text-xs self-center">{s.label}</div>
            <div className="text-sm" style={{ fontFamily: "'JetBrains Mono', monospace", color: !isHudWinner ? "#ffffff" : "#8888AA" }}>{s.oai}</div>
          </div>
        ))}
      </motion.div>

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.3 }} className="flex gap-4 mt-8 relative z-10">
        <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.98 }} onClick={() => navigate("/")} className="px-8 py-3 rounded-full cursor-pointer tracking-wider" style={{ background: "linear-gradient(135deg, #FFB800, #D4AF37)", color: "#0A0A0F", fontFamily: "'Playfair Display', serif", fontWeight: 700 }}>
          RUN AGAIN
        </motion.button>
        <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.98 }} onClick={() => setShowLog(!showLog)} className="px-8 py-3 rounded-full cursor-pointer tracking-wider" style={{ background: "transparent", border: "1px solid #1E1E2E", color: "#8888AA" }}>
          {showLog ? "HIDE TRADE LOG" : "VIEW TRADE LOG"}
        </motion.button>
      </motion.div>

      {showLog && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-6 w-full max-w-2xl rounded-xl p-4 relative z-10 max-h-[200px] overflow-y-auto" style={{ background: "#14141F", border: "1px solid #1E1E2E", fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#8888AA" }}>
          <div className="space-y-1">
            {result.trades_timeline.map((trade, idx) => (
              <div key={idx}>
                {String(trade.date || "")}: {String(trade.agent || "")} {String(trade.action || "HOLD")} @ ${Number(trade.price || 0).toFixed(2)}
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
