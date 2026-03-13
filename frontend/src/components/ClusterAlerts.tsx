"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { AlertTriangle, Users, Target, TrendingUp, ChevronRight, Crosshair } from "lucide-react"
import { ClusterAlert } from "@/types"

function formatCurrency(num: number, compact = true) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        notation: compact ? "compact" : "standard",
        maximumFractionDigits: compact ? 1 : 0
    }).format(num);
}

function timeAgo(dateStr: string) {
    const diff = Date.now() - new Date(dateStr).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return "Just now"
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
}

function getConfidenceColor(c: number) {
    if (c >= 0.8) return "text-emerald-400"
    if (c >= 0.5) return "text-yellow-400"
    return "text-orange-400"
}

function getConfidenceBg(c: number) {
    if (c >= 0.8) return "bg-emerald-500/10 border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
    if (c >= 0.5) return "bg-yellow-500/10 border-yellow-500/20"
    return "bg-orange-500/10 border-orange-500/20"
}

interface ClusterAlertsProps {
    initialAlerts: ClusterAlert[];
    onCopyTrade?: (alert: ClusterAlert) => void;
}

export function ClusterAlerts({ initialAlerts, onCopyTrade }: ClusterAlertsProps) {
    const [alerts, setAlerts] = React.useState<ClusterAlert[]>(initialAlerts)
    const [loading, setLoading] = React.useState(false)
    const [scanning, setScanning] = React.useState(false)

    const fetchAlerts = React.useCallback(async () => {
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/tracker/clusters/alerts?limit=10`)
            if (res.ok) {
                const data = await res.json()
                setAlerts(data || [])
            }
        } catch (err) {
            console.error("Failed to fetch cluster alerts", err)
        } finally {
            setLoading(false)
        }
    }, [])

    React.useEffect(() => {
        const interval = setInterval(fetchAlerts, 15000)
        return () => clearInterval(interval)
    }, [fetchAlerts])

    const handleScan = async () => {
        setScanning(true)
        try {
            await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/tracker/clusters/scan`, { method: "POST" })
            await fetchAlerts()
        } catch (err) {
            console.error("Scan failed", err)
        } finally {
            setScanning(false)
        }
    }

    const parseArray = (val: any): string[] => {
        if (Array.isArray(val)) return val;
        try {
            return JSON.parse(val)
        } catch {
            return []
        }
    }

    return (
        <Card className="w-full bg-slate-950/40 border-slate-800 backdrop-blur-md relative overflow-hidden shadow-2xl">
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-emerald-500/5 rounded-full blur-[100px] pointer-events-none" />

            <CardHeader className="pb-4 border-b border-white/5">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-bold tracking-tighter flex items-center gap-2 text-slate-100 uppercase">
                        <AlertTriangle className="w-4 h-4 text-orange-500 animate-pulse" />
                        <span>Cluster Detection</span>
                        {alerts.length > 0 && (
                            <span className="ml-2 px-2.5 py-0.5 bg-orange-500/10 text-orange-400 text-[10px] font-black rounded-full border border-orange-500/20 uppercase tracking-widest">
                                {alerts.length} ALERTS
                            </span>
                        )}
                    </CardTitle>
                    <button
                        onClick={handleScan}
                        disabled={scanning}
                        className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-slate-300 text-[10px] uppercase font-black tracking-[0.2em] px-4 py-2 rounded border border-white/10 transition-all disabled:opacity-50 active:scale-95"
                    >
                        <Crosshair className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
                        {scanning ? 'SWEEPING…' : 'RUN BEAM SCAN'}
                    </button>
                </div>
            </CardHeader>

            <CardContent className="pt-6">
                {loading && alerts.length === 0 ? (
                    <div className="py-12 text-center text-slate-500 animate-pulse font-mono text-xs uppercase tracking-widest">
                        Initializing cluster detection…
                    </div>
                ) : alerts.length === 0 ? (
                    <div className="py-16 flex flex-col items-center gap-6">
                        <div className="relative">
                            <div className="w-20 h-20 border-2 border-slate-800 rounded-full flex items-center justify-center opacity-40">
                                <Users className="w-8 h-8 text-slate-500" />
                            </div>
                        </div>
                        <div className="text-center">
                            <p className="text-[10px] text-slate-500 uppercase tracking-[0.3em] font-black mb-2">No Active Signal</p>
                            <p className="text-[10px] text-slate-600 max-w-[200px] leading-relaxed font-bold uppercase tracking-tighter">
                                Pulse scan results: Negative convergence across all secondary vectors.
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {alerts.map((alert) => {
                            const grades = parseArray(alert.wallet_grades)
                            return (
                                <div
                                    key={alert.alert_id}
                                    className="group p-5 rounded-lg bg-white/[0.02] border border-white/5 hover:border-emerald-500/30 transition-all duration-300 shadow-xl"
                                >
                                    <div className="flex items-start justify-between gap-4 mb-4">
                                        <div className="flex-1 min-w-0">
                                            <h4 className="text-sm font-black text-slate-100 leading-tight group-hover:text-emerald-400 transition-colors uppercase tracking-tighter">
                                                {alert.market_question || "Classified Market"}
                                            </h4>
                                            <div className="flex items-center gap-3 mt-3">
                                                <span className={`px-2.5 py-0.5 rounded text-[9px] font-black uppercase border ${alert.outcome === "YES"
                                                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                                    : "bg-red-500/10 text-red-500 border-red-500/20"
                                                    }`}>
                                                    {alert.outcome}
                                                </span>
                                                <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">
                                                    {timeAgo(alert.detected_at)}
                                                </span>
                                            </div>
                                        </div>

                                        <div className={`flex flex-col items-center justify-center min-w-[70px] px-3 py-2 rounded-lg border ${getConfidenceBg(alert.confidence)}`}>
                                            <span className={`text-lg font-black font-mono tracking-tighter ${getConfidenceColor(alert.confidence)}`}>
                                                {(alert.confidence * 100).toFixed(0)}%
                                            </span>
                                            <span className="text-[8px] text-slate-500 uppercase font-black tracking-tighter">SIGNAL</span>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-6 mb-4 border-y border-white/[0.02] py-3">
                                        <div className="flex flex-col">
                                            <span className="text-[8px] uppercase text-slate-500 font-black mb-1">Nodes</span>
                                            <div className="flex items-center gap-1.5">
                                                <Users className="w-3 h-3 text-emerald-500" />
                                                <span className="text-[10px] font-black text-slate-200">{alert.wallet_count}</span>
                                            </div>
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-[8px] uppercase text-slate-500 font-black mb-1">Concentration</span>
                                            <div className="flex items-center gap-1.5 text-blue-400">
                                                <Target className="w-3 h-3" />
                                                <span className="text-[10px] font-black">{formatCurrency(alert.total_exposure)}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between mt-4">
                                        <div className="flex -space-x-1.5">
                                            {grades.slice(0, 5).map((g, i) => (
                                                <div
                                                    key={i}
                                                    title={g}
                                                    className={`w-6 h-6 rounded-full border-2 border-slate-900 flex items-center justify-center text-[7px] font-black ${g === "WHALE" ? "bg-purple-600 text-white" :
                                                        g === "SHARK" ? "bg-blue-600 text-white" :
                                                            "bg-emerald-600 text-white"
                                                        }`}
                                                >
                                                    {g[0]}
                                                </div>
                                            ))}
                                            {grades.length > 5 && (
                                                <div className="w-6 h-6 rounded-full border-2 border-slate-900 bg-slate-800 flex items-center justify-center text-[7px] font-black text-slate-400">
                                                    +{grades.length - 5}
                                                </div>
                                            )}
                                        </div>

                                        {onCopyTrade && (
                                            <button
                                                onClick={() => onCopyTrade(alert)}
                                                className="flex items-center gap-1 px-3 py-1.5 bg-white text-slate-950 rounded text-[9px] font-black uppercase tracking-widest hover:bg-emerald-400 transition-all transform hover:scale-105 active:scale-95 shadow-lg"
                                            >
                                                SYNK SIGNAL
                                                <ChevronRight className="w-3 h-3" />
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                )}
            </CardContent>
        </Card>
    )
}
