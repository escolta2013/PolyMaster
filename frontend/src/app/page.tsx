import * as React from "react"
import { Suspense } from "react";
import { SmartMoneyTable } from "@/components/SmartMoneyTable";
import { SmartMoneyWallets } from "@/components/SmartMoneyWallets";
import { ClusterAlerts } from "@/components/ClusterAlerts";
import { Shield, Globe } from "lucide-react";
import { LiveStats } from "@/components/LiveStats";
import { LiveSystemStatus } from "@/components/LiveSystemStatus";
import { getStats, getTopMarkets, getWallets, getClusterAlerts } from "@/lib/api";

// SEO Metadata
export const metadata = {
  title: "PolyMaster v2.0 | Institutional-Grade Intelligence",
  description: "Real-time smart money tracking and algorithmic trading for Polymarket.",
};

export default async function Home() {
  // Parallel data fetching for initial load
  const [initialStats, initialMarkets, initialWallets, initialAlerts] = await Promise.all([
    getStats(),
    getTopMarkets(10),
    getWallets(20),
    getClusterAlerts(10)
  ]);

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
        <LiveSystemStatus />
      </div>

      {/* KPI Cards - Client Component for auto-refresh */}
      <Suspense fallback={<StatsSkeleton />}>
        <LiveStats initialStats={initialStats} />
      </Suspense>

      {/* Main Grid - 2 columns for Cluster + Markets */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cluster Alerts — left column */}
        <div className="lg:col-span-1">
          <Suspense fallback={<CardSkeleton />}>
            <ClusterAlerts initialAlerts={initialAlerts} />
          </Suspense>
        </div>
        {/* Right content — stack tables */}
        <div className="lg:col-span-2 space-y-10">
          <Suspense fallback={<CardSkeleton />}>
            <SmartMoneyTable initialMarkets={initialMarkets} />
          </Suspense>
          <Suspense fallback={<CardSkeleton />}>
            <SmartMoneyWallets initialWallets={initialWallets} />
          </Suspense>
        </div>
      </div>
    </div>
  );
}

function StatsSkeleton() {
  return <div className="grid grid-cols-1 md:grid-cols-5 gap-5 animate-pulse">
    {[...Array(5)].map((_, i) => (
      <div key={i} className="h-32 bg-slate-900/40 rounded-lg border border-white/5" />
    ))}
  </div>;
}

function CardSkeleton() {
  return <div className="w-full h-[400px] bg-slate-900/20 rounded-lg border border-white/5 animate-pulse" />;
}
