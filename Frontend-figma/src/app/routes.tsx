import { createBrowserRouter } from "react-router";
import { StockSelector } from "./components/StockSelector";
import { LiveSimulation } from "./components/LiveSimulation";
import { WinnerAnnouncement } from "./components/WinnerAnnouncement";

export const router = createBrowserRouter([
  { path: "/", Component: StockSelector },
  { path: "/simulation", Component: LiveSimulation },
  { path: "/winner", Component: WinnerAnnouncement },
]);
