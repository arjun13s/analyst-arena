export interface AgentPayload {
  name: string;
  display_name: string;
  provider: string;
  model_id: string;
  accent_color: string;
  initial_cash: number;
  final_portfolio_value: number;
  total_return_pct: number;
  max_drawdown_pct: number;
  trade_count: number;
  win_rate: number;
  elapsed_seconds: number;
  winner: boolean;
  equity_curve: Array<Record<string, unknown>>;
  trade_log: Array<Record<string, unknown>>;
}

export interface SimulationFrame {
  frame: number;
  date: string;
  agent_a_equity: number;
  agent_b_equity: number;
  agent_a_return_pct: number;
  agent_b_return_pct: number;
}

export interface MatchResultPayload {
  match_id: string;
  ticker: string;
  start_date: string;
  end_date: string;
  initial_cash: number;
  total_frames: number;
  agent_a: AgentPayload;
  agent_b: AgentPayload;
  simulation_frames: SimulationFrame[];
  trades_timeline: Array<Record<string, unknown>>;
  winner: string;
  loser: string;
  winner_display_name: string;
  loser_display_name: string;
  winner_final_value: number;
  loser_final_value: number;
  return_diff_pct: number;
  trophy: boolean;
  reasoning: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function runMatch(ticker: string): Promise<MatchResultPayload> {
  const response = await fetch(`${API_BASE}/api/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      agent_a: "hud_model",
      agent_b: "gpt4o",
      ticker,
      months: 1,
      starting_cash: 100000,
    }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Failed to run match (${response.status})`);
  }
  return (await response.json()) as MatchResultPayload;
}
