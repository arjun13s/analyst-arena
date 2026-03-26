import { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { motion } from "motion/react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts";
import { MatchResultPayload, runMatch } from "./api";

/** Blocks duplicate POST /api/match when React 18 Strict Mode runs the effect twice in dev (would start two full backtests). */
const _matchFetchInFlight = new Set<string>();

function OpenAILogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z" />
    </svg>
  );
}

export function LiveSimulation() {
  const [searchParams] = useSearchParams();
  const ticker = searchParams.get("ticker") || "NVDA";
  const navigate = useNavigate();
  const [result, setResult] = useState<MatchResultPayload | null>(null);
  const [loadError, setLoadError] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [frame, setFrame] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const key = ticker.toUpperCase();
    // React 18 Strict Mode runs this effect twice in dev; second run must not start another match.
    if (_matchFetchInFlight.has(key)) {
      return;
    }
    setIsLoading(true);
    setLoadError("");
    _matchFetchInFlight.add(key);
    runMatch(ticker)
      .then((payload) => {
        sessionStorage.setItem(`match:${payload.match_id}`, JSON.stringify(payload));
        setResult(payload);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        setLoadError(err instanceof Error ? err.message : "Failed to load simulation");
        setIsLoading(false);
      })
      .finally(() => {
        _matchFetchInFlight.delete(key);
      });
  }, [ticker]);

  const totalFrames = result?.simulation_frames.length ?? 0;

  useEffect(() => {
    if (!result || totalFrames <= 0) return;
    setFrame(0);
    intervalRef.current = setInterval(() => {
      setFrame((prev) => {
        if (prev >= totalFrames - 1) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          return totalFrames - 1;
        }
        return prev + 1;
      });
    }, 160);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [result, totalFrames]);

  const done = totalFrames > 0 && frame >= totalFrames - 1;
  useEffect(() => {
    if (done && result) {
      const timeout = setTimeout(() => navigate(`/winner?matchId=${result.match_id}`), 1500);
      return () => clearTimeout(timeout);
    }
  }, [done, navigate, result]);

  if (isLoading) return <div className="min-h-screen w-full flex items-center justify-center text-[#8888AA]">Running simulation...</div>;
  if (loadError || !result) return <div className="min-h-screen w-full flex items-center justify-center text-red-400">{loadError || "Missing result"}</div>;

  const frames = result.simulation_frames;
  const current = frames[Math.min(frame, frames.length - 1)];
  const chartData = frames.slice(0, frame + 1).map((item, i) => ({ day: item.date, hud: item.agent_a_equity, oai: item.agent_b_equity, index: i }));
  const allVals = chartData.flatMap((p) => [p.hud, p.oai]);
  const yMin = Math.floor(Math.min(...allVals) / 1000) * 1000 - 1000;
  const yMax = Math.ceil(Math.max(...allVals) / 1000) * 1000 + 1000;
  const progress = ((frame + 1) / totalFrames) * 100;
  const visibleTrades = result.trades_timeline
    .slice(0, Math.min(result.trades_timeline.length, frame * 2 + 1))
    .slice(-6)
    .map((trade) => `${String(trade.agent || "Agent")}: ${String(trade.action || "HOLD")} @ $${Number(trade.price || 0).toFixed(2)}`);
  const fmt = (v: number) => "$" + v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  return (
    <div className="min-h-screen w-full flex flex-col overflow-hidden" style={{ background: "#0A0A0F", fontFamily: "Inter, sans-serif" }}>
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#1E1E2E]">
        <span className="text-white tracking-wider" style={{ fontFamily: "'Playfair Display', serif", fontWeight: 900, fontSize: "20px" }}>ANALYST ARENA</span>
        <div className="flex flex-col items-center flex-1 mx-8">
          <span className="text-[#8888AA] text-sm mb-1">AI vs AI showdown</span>
          <div className="w-full max-w-md h-1.5 rounded-full bg-[#1E1E2E] overflow-hidden">
            <motion.div className="h-full rounded-full" style={{ background: "linear-gradient(90deg, #FFB800, #D4AF37)", width: `${progress}%` }} />
          </div>
        </div>
        <span className="px-4 py-1.5 rounded-full text-sm" style={{ background: "rgba(255,184,0,0.15)", color: "#FFB800", fontFamily: "'JetBrains Mono', monospace" }}>
          {ticker}
        </span>
      </div>

      <div className="flex-1 flex gap-4 p-4" style={{ minHeight: 0 }}>
        <div className="flex-1 rounded-xl p-4 flex flex-col" style={{ background: "#14141F", border: "1px solid #1E1E2E" }}>
          <div className="flex items-center gap-2 mb-3">
            <div className="bg-white rounded px-1.5 py-0.5">
              <img src="/hud-logo.png" alt="HUD logo" className="h-4 object-contain" />
            </div>
            <span className="text-[#8888AA] text-sm">hud</span>
          </div>
          <div className="flex-1" style={{ minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}><CartesianGrid stroke="#1E1E2E" strokeDasharray="3 3" /><XAxis dataKey="day" tick={{ fill: "#8888AA", fontSize: 11 }} tickLine={false} axisLine={false} interval={Math.floor(totalFrames / 6)} /><YAxis domain={[yMin, yMax]} tick={{ fill: "#8888AA", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} /><Line type="monotone" dataKey="hud" stroke="#FFB800" strokeWidth={2} dot={false} isAnimationActive={false} /></LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 text-center">
            <div className="text-3xl text-white" style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, textShadow: "0 0 20px rgba(255,184,0,0.4)" }}>{fmt(current.agent_a_equity)}</div>
            <div className="text-sm mt-1" style={{ fontFamily: "'JetBrains Mono', monospace", color: current.agent_a_return_pct >= 0 ? "#00DD77" : "#FF4466" }}>Total Return: {current.agent_a_return_pct >= 0 ? "+" : ""}{current.agent_a_return_pct.toFixed(2)}%</div>
          </div>
        </div>

        <div className="flex-1 rounded-xl p-4 flex flex-col" style={{ background: "#14141F", border: "1px solid #1E1E2E" }}>
          <div className="flex items-center gap-2 mb-3"><OpenAILogo className="h-5 w-5 text-[#8888AA]" /><span className="text-[#8888AA] text-sm">ChatGPT</span></div>
          <div className="flex-1" style={{ minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}><CartesianGrid stroke="#1E1E2E" strokeDasharray="3 3" /><XAxis dataKey="day" tick={{ fill: "#8888AA", fontSize: 11 }} tickLine={false} axisLine={false} interval={Math.floor(totalFrames / 6)} /><YAxis domain={[yMin, yMax]} tick={{ fill: "#8888AA", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} /><Line type="monotone" dataKey="oai" stroke="#10A37F" strokeWidth={2} dot={false} isAnimationActive={false} /></LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 text-center">
            <div className="text-3xl text-white" style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, textShadow: "0 0 20px rgba(16,163,127,0.4)" }}>{fmt(current.agent_b_equity)}</div>
            <div className="text-sm mt-1" style={{ fontFamily: "'JetBrains Mono', monospace", color: current.agent_b_return_pct >= 0 ? "#00DD77" : "#FF4466" }}>Total Return: {current.agent_b_return_pct >= 0 ? "+" : ""}{current.agent_b_return_pct.toFixed(2)}%</div>
          </div>
        </div>
      </div>

      <div className="px-6 py-2 border-t border-[#1E1E2E] overflow-hidden whitespace-nowrap" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#8888AA" }}>
        {visibleTrades.join("  |  ")}
      </div>
    </div>
  );
}
