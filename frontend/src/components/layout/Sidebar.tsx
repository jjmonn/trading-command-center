import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/",          icon: "⬡",  label: "Dashboard"  },
  { to: "/trades",    icon: "📝", label: "Trade Log"  },
  { to: "/portfolio", icon: "💼", label: "Portfolio"  },
  { to: "/signals",   icon: "📡", label: "Signals"    },
  { to: "/markets",   icon: "📊", label: "Markets"    },
  { to: "/ai",        icon: "🤖", label: "AI Analysis"},
  { to: "/greeks",    icon: "Δ",  label: "Greeks"     },
];

export default function Sidebar() {
  return (
    <aside className="w-52 shrink-0 bg-surface-1 border-r border-border flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-border">
        <div className="text-bright font-semibold text-sm">⚡ TCC</div>
        <div className="text-muted text-xs mt-0.5">Command Center</div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `nav-link${isActive ? " active" : ""}`
            }
          >
            <span className="w-5 text-center font-mono text-base">{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border text-xs text-muted">
        Phase 1 · v0.1.0
      </div>
    </aside>
  );
}
