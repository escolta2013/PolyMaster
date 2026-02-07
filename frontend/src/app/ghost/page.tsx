"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Ghost, Zap, Activity, TrendingUp, AlertTriangle, ShieldCheck, Crosshair, BarChart3, Settings2, Play, Square, Power } from "lucide-react"

export default function GhostPage() {
    const [scans, setScans] = React.useState<any[]>([])
    const [status, setStatus] = React.useState<any>(null)
    const [loading, setLoading] = React.useState(true)
    const [grinderSpread, setGrinderSpread] = React.useState(0.02)
    const [grinderSize, setGrinderSize] = React.useState(10)
    const [isArmed, setIsArmed] = React.useState(false) // Execution toggle

    const fetchData = React.useCallback(async () => {
        try {
            const statusRes = await fetch("http://127.0.0.1:8000/ghost/status")
            const scanRes = await fetch("http://127.0.0.1:8000/ghost/scan")

            if (statusRes.ok) {
                const statusData = await statusRes.json()
                setStatus(statusData)
                setIsArmed(!statusData.simulation_mode)
            }
            if (scanRes.ok) setScans(await scanRes.json())
        } catch (error) {
            console.error("Failed to fetch Ghost data", error)
        } finally {
            setLoading(false)
        }
    }, [])

    React.useEffect(() => {
        fetchData()
        const interval = setInterval(fetchData, 10000)
        return () => clearInterval(interval)
    }, [fetchData])

    const toggleExecutionMode = async () => {
        const newArmedState = !isArmed
        try {
            const res = await fetch("http://127.0.0.1:8000/ghost/execution-mode", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ simulation: !newArmedState })
            })
            if (res.ok) {
                setIsArmed(newArmedState)
                fetchData()
            }
        } catch (error) {
            console.error("Error toggling execution mode", error)
        }
    }

    const startStrategy = async (marketId: string, tokenId: string) => {
        try {
            await fetch("http://127.0.0.1:8000/ghost/strategy/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ market_id: marketId, token_id: tokenId })
            })
            alert("Strategy signal sent to engine.")
        } catch (error) {
            console.error("Error starting strategy", error)
        }
    }

    const stopStrategy = async () => {
        try {
            await fetch("http://127.0.0.1:8000/ghost/strategy/stop", { method: "POST" })
            alert("Stop signal sent. All active Ghost orders cancelled.")
        } catch (error) {
            console.error("Error stopping strategy", error)
        }
    }

    return (
        <div className="container mx-auto px-6 py-10 space-y-8 max-w-7xl font-sans selection:bg-purple-500/30">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-8 relative">
                <div className="absolute -top-10 -left-10 w-40 h-40 bg-purple-500/10 rounded-full blur-[100px] pointer-events-none" />
                <div>
                    <h1 className="text-4xl font-black tracking-tighter text-slate-100 flex items-center gap-3">
                        <Ghost className="w-8 h-8 text-purple-500 drop-shadow-[0_0_15px_rgba(168,85,247,0.5)]" />
                        GHOST ENGINE
                        <span className="text-sm font-light text-slate-500 tracking-normal italic uppercase self-end mb-1">v2.1 Tactical</span>
                    </h1>
                    <p className="text-slate-400 text-sm mt-2 font-medium flex items-center gap-2">
                        <ShieldCheck className={`w-3 h-3 ${isArmed ? 'text-red-500' : 'text-emerald-500'}`} />
                        {isArmed ? 'LIVE EXECUTION ARMED' : 'Inert Simulation Mode'}
                    </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                    <button
                        onClick={toggleExecutionMode}
                        className={`px-5 py-2 border rounded-full text-[10px] font-black flex items-center tracking-widest uppercase backdrop-blur-sm transition-all ${isArmed
                            ? 'bg-red-500/10 border-red-500/50 text-red-500 shadow-[0_0_15px_rgba(239,68,68,0.2)]'
                            : 'bg-slate-900/60 border-purple-500/30 text-purple-400'
                            }`}
                    >
                        <Power className={`w-3 h-3 mr-2 ${isArmed ? 'animate-pulse' : ''}`} />
                        {isArmed ? 'ARMED' : 'SAFE'}
                    </button>
                    <div className="text-[9px] text-slate-500 uppercase tracking-tighter">
                        Status: {status?.status || "Analyzing Spectrum..."}
                    </div>
                </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Left: Scanner Feed */}
                <div className="md:col-span-2 space-y-6">
                    <Card className="bg-slate-950/40 border-slate-800 backdrop-blur-xl relative overflow-hidden group">
                        <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent pointer-events-none" />
                        <CardHeader className="pb-4 border-b border-slate-800/50 flex flex-row items-center justify-between relative overflow-hidden">
                            <CardTitle className="text-lg font-semibold tracking-tight text-slate-100 flex items-center gap-2">
                                <Crosshair className="w-4 h-4 text-purple-500 animate-pulse" />
                                Spectral Anomaly Scanner
                            </CardTitle>
                            <span className="text-[10px] uppercase text-slate-500 tracking-widest font-mono flex items-center gap-2">
                                <div className="w-1 h-1 bg-emerald-500 rounded-full animate-pulse" />
                                Real-Time Probability Feed
                            </span>
                        </CardHeader>
                        <CardContent className="pt-0 relative">
                            {/* Scanning Overlay Effect */}
                            <div className="absolute inset-0 pointer-events-none z-20 overflow-hidden opacity-20">
                                <div className="w-full h-[2px] bg-purple-500/50 shadow-[0_0_15px_rgba(168,85,247,0.5)] animate-[scan_3s_ease-in-out_infinite]" />
                                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(2,6,23,0.8)_100%)]" />
                            </div>
                            <div className="divide-y divide-slate-800/30 relative z-10">
                                {loading ? (
                                    <div className="py-20 text-center text-slate-600 animate-pulse font-mono text-xs tracking-widest uppercase">Initializing Quantum Sensors...</div>
                                ) : scans.length === 0 ? (
                                    <div className="py-24 flex flex-col items-center justify-center relative overflow-hidden">
                                        {/* Radar Background Circle */}
                                        <div className="absolute w-64 h-64 border border-purple-500/20 rounded-full" />
                                        <div className="absolute w-40 h-40 border border-purple-500/10 rounded-full" />
                                        <div className="absolute w-20 h-20 border border-purple-500/10 rounded-full" />

                                        {/* Sweeping Radar Arm */}
                                        <div className="absolute w-32 h-32 origin-bottom-right right-1/2 bottom-1/2 animate-[spin_4s_linear_infinite] overflow-hidden pointer-events-none">
                                            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 via-transparent to-transparent -rotate-45" />
                                        </div>

                                        {/* Background Ghost Glow */}
                                        <Ghost className="absolute w-24 h-24 text-purple-500/5 blur-xl animate-pulse" />

                                        {/* Scanning Text */}
                                        <div className="relative z-10 flex flex-col items-center gap-4">
                                            <div className="flex items-center gap-2">
                                                <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-ping" />
                                                <span className="text-[10px] text-purple-400 font-black uppercase tracking-[0.3em] font-mono">Scanning Spectrum</span>
                                            </div>
                                            <p className="text-[10px] text-slate-600 font-mono tracking-wider uppercase max-w-[200px] text-center leading-loose">
                                                Zero Spectral Activity Detected. Monitoring CLOB frequency...
                                            </p>
                                        </div>
                                    </div>
                                ) : (
                                    scans.map((scan, i) => (
                                        <div key={i} className="py-6 hover:bg-white/[0.02] transition-all px-4 -mx-4 group/item cursor-default">
                                            <div className="flex justify-between items-start mb-3">
                                                <div className="space-y-1">
                                                    <h3 className="font-bold text-slate-100 text-sm leading-tight group-hover/item:text-purple-400 transition-colors uppercase tracking-tight">{scan.question}</h3>
                                                    <div className="flex items-center gap-4">
                                                        <span className="text-[10px] text-slate-400 flex items-center gap-1">
                                                            <BarChart3 className="w-2.5 h-2.5" />
                                                            Price: ${scan.price?.toFixed(3)}
                                                        </span>
                                                        <div className="flex items-center gap-1.5 min-w-[120px]">
                                                            <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
                                                                <div
                                                                    className="h-full bg-emerald-500/60 transition-all duration-1000"
                                                                    style={{ width: `${scan.liquidity_score}%` }}
                                                                />
                                                            </div>
                                                            <span className="text-[9px] text-slate-500 font-bold uppercase whitespace-nowrap">Liq Score: {scan.liquidity_score}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex flex-col items-end">
                                                    <span className="text-purple-400 font-black font-mono text-sm drop-shadow-[0_0_8px_rgba(168,85,247,0.3)]">
                                                        +{(scan.spike_magnitude * 100).toFixed(1)}% Intensity
                                                    </span>
                                                    <span className="text-[10px] text-slate-500 font-mono mt-1">{scan.timestamp}</span>
                                                </div>
                                            </div>
                                            <div className="flex justify-between items-center bg-slate-900/40 border border-white/5 py-1.5 px-3 rounded text-[9px] text-slate-500 font-black uppercase tracking-[0.15em]">
                                                <span className="flex items-center gap-2">
                                                    <div className="w-1 h-1 bg-purple-500 rounded-full" />
                                                    Classification: {scan.reason}
                                                </span>
                                                <button
                                                    onClick={() => startStrategy(scan.market_id, scan.token_id)}
                                                    className="text-purple-500/80 hover:text-purple-400 transition-colors tracking-widest border-l border-white/5 pl-3 ml-3 flex items-center gap-1"
                                                >
                                                    <Play className="w-2 h-2" />
                                                    Engage Ghost Trail
                                                </button>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right: Tactical Control */}
                <div className="space-y-6">
                    <Card className="bg-slate-950/40 border-slate-800 backdrop-blur-md">
                        <CardHeader className="pb-4 border-b border-slate-800/50 flex flex-row items-center justify-between">
                            <CardTitle className="text-xs font-bold tracking-[0.1em] text-slate-100 uppercase">Shadow Controls</CardTitle>
                            <Settings2 className="w-3.5 h-3.5 text-slate-600" />
                        </CardHeader>
                        <CardContent className="pt-6 space-y-6">
                            {/* Strategy: Grinder */}
                            <div className="space-y-4">
                                <div className="flex justify-between items-center">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 bg-emerald-500 rounded-sm animate-pulse" />
                                        <span className="text-xs font-black text-slate-100 uppercase tracking-widest">Liquidity Grinder</span>
                                    </div>
                                    <span className="text-[9px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20 font-black uppercase">
                                        {status?.simulation_mode ? 'Simulating' : 'Active'}
                                    </span>
                                </div>

                                <div className="space-y-3 p-3 bg-slate-900/50 rounded border border-white/5">
                                    <div className="space-y-1.5">
                                        <div className="flex justify-between text-[9px] font-bold text-slate-500 uppercase">
                                            <span>Tactical Spread</span>
                                            <span className="text-slate-300">{(grinderSpread * 100).toFixed(1)}%</span>
                                        </div>
                                        <input
                                            type="range" min="0.005" max="0.05" step="0.005"
                                            value={grinderSpread}
                                            onChange={(e) => setGrinderSpread(parseFloat(e.target.value))}
                                            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <div className="flex justify-between text-[9px] font-bold text-slate-500 uppercase">
                                            <span>Position Size</span>
                                            <span className="text-slate-300">${grinderSize} USDC</span>
                                        </div>
                                        <input
                                            type="range" min="5" max="100" step="5"
                                            value={grinderSize}
                                            onChange={(e) => setGrinderSize(parseInt(e.target.value))}
                                            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
                                        />
                                    </div>
                                    <button className="w-full py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 border border-purple-500/30 rounded text-[10px] font-black uppercase tracking-widest transition-all">
                                        Update Grinder Params
                                    </button>
                                </div>
                            </div>

                            {/* Strategy: Shadow Merger */}
                            <StrategyCard
                                title="Shadow Merger"
                                description="Automated position consolidation."
                                status="Standby"
                                color="text-slate-500"
                                icon={<Activity className="w-3 h-3 text-slate-600" />}
                            />

                            <button
                                onClick={stopStrategy}
                                className="w-full py-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded text-[10px] font-black uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-2 mt-4"
                            >
                                <Zap className="w-3 h-3" />
                                Panic Kill-Switch
                            </button>
                        </CardContent>
                    </Card>

                    <Card className="bg-slate-900/40 border-slate-800/50 p-4">
                        <div className="flex items-center gap-3 text-slate-400">
                            <TrendingUp className="w-4 h-4 text-emerald-500" />
                            <div className="flex flex-col">
                                <span className="text-[10px] font-bold uppercase tracking-widest">Est. Daily ROI</span>
                                <span className="text-sm font-mono font-bold text-slate-100">+4.2%</span>
                            </div>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    )
}

function StrategyCard({ title, description, status, color, icon }: any) {
    return (
        <div className="p-4 rounded bg-slate-900/30 border border-white/5 hover:border-white/10 transition-colors">
            <div className="flex justify-between items-center mb-1.5">
                <div className="flex items-center gap-2">
                    {icon}
                    <div className="font-black text-[10px] text-slate-200 uppercase tracking-widest">{title}</div>
                </div>
                <div className={`text-[9px] font-black uppercase ${color}`}>{status}</div>
            </div>
            <p className="text-[10px] text-slate-500 leading-relaxed font-medium">{description}</p>
        </div>
    )
}
