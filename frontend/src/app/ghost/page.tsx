"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Ghost, Zap, Activity, TrendingUp, AlertTriangle } from "lucide-react"

export default function GhostPage() {
    const [scans, setScans] = React.useState<any[]>([])
    const [status, setStatus] = React.useState<any>(null)
    const [loading, setLoading] = React.useState(true)

    React.useEffect(() => {
        async function fetchData() {
            try {
                const statusRes = await fetch("http://127.0.0.1:8000/ghost/status")
                const scanRes = await fetch("http://127.0.0.1:8000/ghost/scan")

                if (statusRes.ok) setStatus(await statusRes.json())
                if (scanRes.ok) setScans(await scanRes.json())
            } catch (error) {
                console.error("Failed to fetch Ghost data", error)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
        const interval = setInterval(fetchData, 10000) // 10s refresh for scanner
        return () => clearInterval(interval)
    }, [])

    return (
        <div className="container mx-auto px-6 py-10 space-y-8 max-w-7xl font-sans selection:bg-purple-500/30">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-8">
                <div>
                    <h1 className="text-4xl font-black tracking-tighter text-slate-100 flex items-center gap-3">
                        <Ghost className="w-8 h-8 text-purple-500" />
                        GHOST ENGINE
                        <span className="text-sm font-light text-slate-500 tracking-normal italic uppercase self-end mb-1">v1.2</span>
                    </h1>
                    <p className="text-slate-400 text-sm mt-2 font-medium">
                        Statistical Arbitrage & Event Scanning
                    </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                    <div className="px-4 py-1.5 bg-purple-500/5 border border-purple-500/20 rounded-sm text-[10px] font-black text-purple-400 flex items-center tracking-widest uppercase">
                        <div className="w-1.5 h-1.5 bg-purple-500 rounded-full mr-3 shadow-[0_0_8px_rgba(168,85,247,0.5)] animate-pulse" />
                        Status: {status?.status || "Connecting..."}
                    </div>
                </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Left: Scanner Feed */}
                <div className="md:col-span-2 space-y-6">
                    <Card className="bg-slate-950/40 border-slate-800 backdrop-blur-md">
                        <CardHeader className="pb-4 border-b border-slate-800/50 flex flex-row items-center justify-between">
                            <CardTitle className="text-lg font-semibold tracking-tight text-slate-100 flex items-center gap-2">
                                <Activity className="w-4 h-4 text-purple-400" />
                                Hype Spike Scanner
                            </CardTitle>
                            <span className="text-[10px] uppercase text-slate-500 tracking-widest font-mono">Live Feed</span>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <div className="divide-y divide-slate-800/50">
                                {loading ? (
                                    <div className="py-12 text-center text-slate-500 italic">Initializing Scanners...</div>
                                ) : scans.length === 0 ? (
                                    <div className="py-12 text-center text-slate-500">No anomalies detected. Market efficient.</div>
                                ) : (
                                    scans.map((scan, i) => (
                                        <div key={i} className="py-4 hover:bg-slate-800/20 transition-colors px-4 -mx-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <h3 className="font-medium text-slate-200 text-sm">{scan.question}</h3>
                                                <span className="text-emerald-400 font-mono font-bold text-xs">
                                                    +{(scan.spike_magnitude * 100).toFixed(0)}% Spike
                                                </span>
                                            </div>
                                            <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono uppercase tracking-wider">
                                                <span className="flex items-center gap-1">
                                                    <AlertTriangle className="w-3 h-3 text-yellow-500/50" />
                                                    {scan.reason}
                                                </span>
                                                <span className="text-slate-400">{scan.timestamp}</span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right: Active Strategies */}
                <div className="space-y-6">
                    <Card className="bg-slate-950/40 border-slate-800 backdrop-blur-md">
                        <CardHeader className="pb-4 border-b border-slate-800/50">
                            <CardTitle className="text-sm font-semibold tracking-tight text-slate-100 uppercase">Active Strategies</CardTitle>
                        </CardHeader>
                        <CardContent className="pt-6 space-y-4">
                            <StrategyCard
                                title="Liquidity Grinder"
                                description="Placing wide NO limits to capture spread."
                                status="Active"
                                color="text-emerald-400"
                            />
                            <StrategyCard
                                title="No-Folio Merger"
                                description="Auto-merging positions to USDC."
                                status="Standby"
                                color="text-yellow-400"
                            />
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}

function StrategyCard({ title, description, status, color }: any) {
    return (
        <div className="p-3 rounded bg-slate-900/50 border border-slate-800/50">
            <div className="flex justify-between items-center mb-1">
                <div className="font-bold text-xs text-slate-300 uppercase tracking-wider">{title}</div>
                <div className={`text-[9px] font-black uppercase ${color}`}>{status}</div>
            </div>
            <p className="text-[10px] text-slate-500">{description}</p>
        </div>
    )
}
