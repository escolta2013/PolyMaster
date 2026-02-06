"use client"

import * as React from "react"
import { SmartMoneyTable } from "@/components/SmartMoneyTable";
import { SmartMoneyWallets } from "@/components/SmartMoneyWallets";
import { TrendingUp, Users, Wallet, Target, Activity, Zap, Shield, Globe } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  const [stats, setStats] = React.useState<any>(null);
  const [mounted, setMounted] = React.useState(false);
  const [syncTime, setSyncTime] = React.useState("");

  React.useEffect(() => {
    setMounted(true);
    setSyncTime(new Date().toLocaleTimeString());

    async function fetchStats() {
      try {
        const res = await fetch("http://127.0.0.1:8000/tracker/stats");
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        }
      } catch (error) {
        console.error("Failed to fetch stats", error);
      }
    }
    fetchStats();
    const interval = setInterval(fetchStats, 30000); // 30s refresh
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="container mx-auto px-6 py-10 space-y-10 max-w-7xl font-sans selection:bg-emerald-500/30">
      {/* Institutional Header */}
      <div className="flex flex-col md:flex-row items-start md:items-end justify-between gap-6 border-b border-white/5 pb-8">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-5 h-5 text-emerald-500" />
            <span className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-500">Security-Grade Intelligence</span>
          </div>
          <h1 className="text-5xl font-black tracking-tighter text-slate-100 flex items-baseline gap-2">
            POLYMASTER <span className="text-xl font-light text-slate-500 tracking-normal italic uppercase">v2.0</span>
          </h1>
          <p className="text-slate-400 text-sm mt-3 flex items-center font-medium">
            <Globe className="w-3.5 h-3.5 mr-2 text-blue-500" />
            Smart Money Tracking Network · Real-time Institutional Flow Analysis
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="px-4 py-1.5 bg-emerald-500/5 border border-emerald-500/20 rounded-sm text-[10px] font-black text-emerald-400 flex items-center tracking-widest uppercase">
            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-3 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse" />
            Quantum-Node: Active
          </div>
          <div className="text-[10px] text-slate-500 font-mono uppercase tracking-tighter">
            Last Block Sync: {mounted ? syncTime : "--:--:--"}
          </div>
        </div>
      </div>

      {/* KPI Cards - Institutional Style */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <KPIItem
          title="Monitored Entities"
          value={stats?.total_tracked || "--"}
          caption="Active Network Signatures"
          icon={<Users className="w-4 h-4 text-slate-400" />}
        />
        <KPIItem
          title="Classified Alpha"
          value={stats?.smart_money_count || "--"}
          caption="Verified Institutional Wallets"
          color="text-purple-400"
          icon={<Zap className="w-4 h-4 text-purple-500" />}
        />
        <KPIItem
          title="Whale Concentration"
          value={stats?.by_grade?.WHALE || "--"}
          caption="High-Liquidity Nodes"
          color="text-blue-400"
          icon={<Target className="w-4 h-4 text-blue-500" />}
        />
        <KPIItem
          title="Network Volume"
          value="$1.4M"
          caption="24h Aggregate Exposure"
          color="text-emerald-500"
          icon={<TrendingUp className="w-4 h-4 text-emerald-500" />}
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 gap-12">
        <div className="space-y-12">
          <SmartMoneyTable />
          <SmartMoneyWallets />
        </div>
      </div>
    </div>
  );
}

function KPIItem({ title, value, caption, icon, color = "text-slate-100" }: { title: string, value: string | number, caption: string, icon: React.ReactNode, color?: string }) {
  return (
    <Card className="bg-slate-900/20 border-white/5 backdrop-blur-md hover:border-white/10 transition-all duration-300 shadow-xl">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">{title}</CardTitle>
        <div className="opacity-40">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className={`text-3xl font-black tracking-tighter ${color}`}>{value}</div>
        <p className="text-[9px] text-slate-500 font-bold uppercase mt-2 tracking-widest">{caption}</p>
      </CardContent>
    </Card>
  )
}
