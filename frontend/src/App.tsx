import { BrowserRouter, Route, Routes } from "react-router-dom";
import Sidebar from "./components/layout/Sidebar";
import Dashboard from "./pages/Dashboard";
import TradeLog from "./pages/TradeLog";

function Placeholder({ label }: { label: string }) {
  return (
    <div className="flex-1 flex items-center justify-center text-muted text-lg">
      {label} — coming in a later phase
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-surface">
        <Sidebar />
        <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
          <Routes>
            <Route path="/"          element={<Dashboard />} />
            <Route path="/trades"    element={<TradeLog />} />
            <Route path="/portfolio" element={<Placeholder label="Portfolio" />} />
            <Route path="/signals"   element={<Placeholder label="Social Signals" />} />
            <Route path="/markets"   element={<Placeholder label="Market Trends" />} />
            <Route path="/ai"        element={<Placeholder label="AI Analysis" />} />
            <Route path="/greeks"    element={<Placeholder label="Greeks" />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
