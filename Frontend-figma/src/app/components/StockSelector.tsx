import { useState } from "react";
import { useNavigate } from "react-router";
import { motion } from "motion/react";
import { Zap } from "lucide-react";

const stocks = [
  { ticker: "NVDA", name: "NVIDIA" },
  { ticker: "AAPL", name: "Apple" },
  { ticker: "GOOGL", name: "Alphabet" },
];

function OpenAILogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z" />
    </svg>
  );
}

export function StockSelector() {
  const [selected, setSelected] = useState("NVDA");
  const navigate = useNavigate();

  return (
    <div
      className="min-h-screen w-full flex flex-col items-center justify-center relative overflow-hidden"
      style={{
        background: "radial-gradient(ellipse at center, #1a1a2e 0%, #0A0A0F 70%)",
        fontFamily: "Inter, sans-serif",
      }}
    >
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: "linear-gradient(#ffffff 1px, transparent 1px), linear-gradient(90deg, #ffffff 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      <motion.div initial={{ opacity: 0, y: -30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }} className="text-center mb-12 relative z-10">
        <h1
          className="text-[56px] tracking-wider text-white mb-2"
          style={{ fontFamily: "'Playfair Display', serif", fontWeight: 900, textShadow: "0 0 40px rgba(255,184,0,0.3)" }}
        >
          ANALYST ARENA
        </h1>
        <p className="text-[#8888AA] tracking-widest">AI vs AI — 10 Day Trading Showdown</p>
      </motion.div>

      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.6, delay: 0.3 }} className="flex items-center gap-8 mb-12 relative z-10">
        <div className="w-[260px] h-[200px] rounded-xl flex flex-col items-center justify-center gap-3" style={{ background: "#14141F", border: "1px solid rgba(255,184,0,0.3)", boxShadow: "0 0 30px rgba(255,184,0,0.15), inset 0 0 30px rgba(255,184,0,0.05)" }}>
          <div className="bg-white rounded-lg px-3 py-2">
            <img src="/hud-logo.png" alt="HUD logo" className="h-12 object-contain" />
          </div>
          <span className="text-white mt-1">hud</span>
          <span className="px-3 py-1 rounded-full text-xs" style={{ background: "rgba(255,184,0,0.15)", color: "#FFB800", fontFamily: "'JetBrains Mono', monospace" }}>
            hud-ai-v1
          </span>
        </div>

        <div className="flex flex-col items-center">
          <div className="relative">
            <Zap className="absolute -top-3 -left-3 w-5 h-5 text-yellow-400 opacity-60" />
            <span className="text-5xl tracking-tight" style={{ fontFamily: "'Playfair Display', serif", fontWeight: 900, background: "linear-gradient(135deg, #FFB800, #D4AF37)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", filter: "drop-shadow(0 0 20px rgba(255,184,0,0.4))" }}>
              VS
            </span>
            <Zap className="absolute -bottom-3 -right-3 w-5 h-5 text-yellow-400 opacity-60" />
          </div>
          <div className="w-px h-8 bg-gradient-to-b from-[#FFB800] to-[#D4AF37] opacity-40 mt-2" />
        </div>

        <div className="w-[260px] h-[200px] rounded-xl flex flex-col items-center justify-center gap-3" style={{ background: "#14141F", border: "1px solid rgba(16,163,127,0.3)", boxShadow: "0 0 30px rgba(16,163,127,0.15), inset 0 0 30px rgba(16,163,127,0.05)" }}>
          <OpenAILogo className="h-12 w-12 text-white" />
          <span className="text-white mt-1">ChatGPT</span>
          <span className="px-3 py-1 rounded-full text-xs" style={{ background: "rgba(16,163,127,0.15)", color: "#10A37F", fontFamily: "'JetBrains Mono', monospace" }}>
            ChatGPT
          </span>
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.5 }} className="flex gap-4 mb-10 relative z-10">
        {stocks.map((s) => {
          const isSelected = selected === s.ticker;
          return (
            <button key={s.ticker} onClick={() => setSelected(s.ticker)} className="flex flex-col items-center gap-1 transition-all duration-200">
              <div
                className="px-6 py-2.5 rounded-full transition-all duration-200"
                style={{
                  background: isSelected ? "linear-gradient(135deg, #FFB800, #D4AF37)" : "transparent",
                  border: isSelected ? "1px solid transparent" : "1px solid #1E1E2E",
                  color: isSelected ? "#0A0A0F" : "#8888AA",
                  boxShadow: isSelected ? "0 0 20px rgba(255,184,0,0.3)" : "none",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontWeight: isSelected ? 700 : 400,
                }}
              >
                {s.ticker}
              </div>
              <span className="text-xs text-[#8888AA]">{s.name}</span>
            </button>
          );
        })}
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.7 }} className="flex flex-col items-center gap-2 relative z-10">
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => navigate(`/simulation?ticker=${selected}`)}
          className="px-12 py-4 rounded-full text-[#0A0A0F] tracking-wider cursor-pointer"
          style={{ background: "linear-gradient(135deg, #FFB800, #D4AF37)", boxShadow: "0 0 30px rgba(255,184,0,0.3), 0 0 60px rgba(255,184,0,0.15)", fontFamily: "'Playfair Display', serif", fontWeight: 700, fontSize: "18px" }}
        >
          START SHOWDOWN
        </motion.button>
        <span className="text-[#8888AA] text-xs" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
          $100,000 starting cash — 3 month window
        </span>
      </motion.div>
    </div>
  );
}
