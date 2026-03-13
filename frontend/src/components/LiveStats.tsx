"use client"

import * as React from "react"
import { TrendingUp, Users, Target, Activity, Zap, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MarketStats } from "@/types";

interface LiveStatsProps {
    initialStats: MarketStats;
}

function formatCompactNumber(num: number) {
    return Intl.NumberFormat('en-US', {
        notation: "compact",
        maximumFractionDigits: 1
    }).format(num);
}

export function LiveStats({ initialStats }: LiveStatsProps) {
    const [stats, setStats] = React.useState<MarketStats>(initialStats);

    React.useEffect(() => {
        async function fetchStats() {
            try {
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/tracker/stats`);
                if (res.ok) {
                    const data = await res.json();
                    setStats(data);
                }
            } catch (error) {
                console.error("Failed to fetch stats", error);
            }
        }
        const interval = setInterval(fetchStats, 30000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-5">
            <KPIItem
                title="Monitored Entities"
                value={stats.total_tracked.toLocaleString()}
                caption="Active Network Signatures"
                icon={<Users className="w-4 h-4 text-slate-400" />}
            />
            <KPIItem
                title="Classified Alpha"
                value={stats.smart_money_count.toLocaleString()}
                caption="Verified Institutional Wallets"
                color="text-purple-400"
                icon={<Zap className="w-4 h-4 text-purple-500" />}
            />
            <KPIItem
                title="Whale Concentration"
                value={stats.by_grade?.WHALE.toLocaleString()}
                caption="High-Liquidity Nodes"
                color="text-blue-400"
                icon={<Target className="w-4 h-4 text-blue-500" />}
            />
            <KPIItem
                title="Cluster Alerts"
                value={stats.cluster_alerts.toLocaleString()}
                caption="Active Convergence Events"
                color="text-orange-400"
                icon={<AlertTriangle className="w-4 h-4 text-orange-500" />}
            />
            <KPIItem
                title="Network Volume"
                value={`$${formatCompactNumber(stats.total_volume)}`}
                caption="24h Aggregate Exposure"
                color="text-emerald-500"
                icon={<TrendingUp className="w-4 h-4 text-emerald-500" />}
            />
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
