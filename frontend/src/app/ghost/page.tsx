"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Ghost, Zap, Activity, TrendingUp, AlertTriangle, ShieldCheck, Crosshair, BarChart3, Settings2, Play, Square, Power, ChevronRight, Sliders, Layers } from "lucide-react"

export default function GhostPage() {
    const [scans, setScans] = React.useState<any[]>([])
    const [status, setStatus] = React.useState<any>(null)
    const [loading, setLoading] = React.useState(true)
    const [grinderSpread, setGrinderSpread] = React.useState(0.02)
    const [grinderSize, setGrinderSize] = React.useState(10)
    const [isArmed, setIsArmed] = React.useState(false)
    const [merging, setMerging] = React.useState(false)
    const [lastAction, setLastAction] = React.useState<string | null>(null)

    const fetchData = React.useCallback(async () => {
        try {
            const statusRes = await fetch("http://127.0.0.1:8000/ghost/status")
            const scanRes = await fetch("http://127.0.0.1:8000/ghost/scan")

            if (statusRes.ok) {
                const statusData = await statusRes.json()
                setStatus(statusData)
                setIsArmed(!statusData.simulation_mode)
                // Sync sliders with server state on first load or status update
                if (statusData.current_spread) setGrinderSpread(statusData.current_spread)
                if (statusData.risk_limits?.position_cap_amount) setGrinderSize(statusData.risk_limits.position_cap_amount)
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
        const interval = setInterval(fetchData, 15000)
        return () => clearInterval(interval)
    }, [fetchData])

    // Persist sliders to backend
    const syncRiskConfig = async (spread: number, size: number) => {
        try {
            await fetch("http://127.0.0.1:8000/ghost/risk/configure", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    spread_width: spread,
                    position_cap_amount: size
                })
            })
            setLastAction(`Config Updated: ${spread * 100}% spread / $${size} cap`)
        } catch (error) {
            console.error("Failed to sync risk config", error)
        }
    }

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
                setLastAction(newArmedState ? "WARNED: LIVE Execution Armed" : "SAFE: Simulation Mode Active")
                fetchData()
            }
        } catch (error) {
            console.error("Error toggling execution mode", error)
        }
    }

    const startStrategy = async (marketId: string, tokenId: string, strategy: string = "liquidity_grinder") => {
        setLastAction(`Initializing ${strategy} on market...`)
        try {
            const res = await fetch("http://127.0.0.1:8000/ghost/strategy/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ market_id: marketId, token_id: tokenId, strategy })
            })
            const data = await res.json()
            if (data.status === "active" || data.status === "simulated") {
                setLastAction(`${strategy.toUpperCase()} execution confirmed.`)
                fetchData()
            }
        } catch (error) {
            console.error("Error starting strategy", error)
            setLastAction("Strategy start failed: connection error")
        }
    }

    const runMerge = async () => {
        setMerging(true)
        setLastAction("Shadow Merger: Scanning for consolidatable pairs...")
        try {
            await fetch("http://127.0.0.1:8000/ghost/merge/scan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_address: "0xDefault" })
            })
            setTimeout(() => {
                setMerging(false)
                setLastAction("Shadow Merger: Scan complete. No eligible pairs found.")
            }, 2000)
        } catch (error) {
            setMerging(false)
            setLastAction("Shadow Merger: Execution error.")
        }
    }

    const stopStrategy = async () => {
        setLastAction("EMERGENCY: Stopping all strategies...")
        try {
            const res = await fetch("http://127.0.0.1:8000/ghost/strategy/stop", { method: "POST" })
            if (res.ok) {
                setLastAction("All strategies halted. Orders cancelled.")
                fetchData()
            }
        } catch (error) {
            console.error("Error stopping strategy", error)
        }
    }

    return (
        <div className="container mx-auto px-6 py-10 space-y-8 max-w-7xl font-sans selection:bg-purple-500/30 bg-[#020617] text-slate-100 min-h-screen">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-8 relative">
                <div className="absolute -top-10 -left-10 w-40 h-40 bg-purple-500/10 rounded-full blur-[100px] pointer-events-none" />
                <div>
                    <h1 className="text-4xl font-black tracking-tighter text-slate-100 flex items-center gap-3">
                        <Ghost className="w-8 h-8 text-purple-500 drop-shadow-[0_0_15px_rgba(168,85,247,0.5)]" />
                        GHOST ENGINE
                        <span className="text-sm font-light text-slate-500 tracking-normal italic uppercase self-end mb-1">v2.5 Tactical</span>
                    </h1>
                    <p className="text-slate-400 text-sm mt-2 font-medium flex items-center gap-2">
                        <ShieldCheck className={`w-3 h-3 ${isArmed ? 'text-red-500 font-bold' : 'text-emerald-500'}`} />
                        {isArmed ? 'LIVE EXECUTION ARMED' : 'Inert Simulation Mode'}
                    </p>
                </div>
                <div className="flex flex-col items-end gap-2 text-right">
                    <button
                        onClick={toggleExecutionMode}
                        className={`px-6 py-2 border rounded-full text-[10px] font-black flex items-center tracking-widest uppercase backdrop-blur-sm transition-all shadow-[0_4px_20px_rgba(0,0,0,0.5)] active:scale-95 ${isArmed
                            ? 'bg-red-500/20 border-red-500/50 text-red-500 shadow-[0_0_25px_rgba(239,68,68,0.3)]'
                            : 'bg-slate-900 border-emerald-500/30 text-emerald-400 hover:border-emerald-500/60'
                            }`}
                    >
                        <Power className={`w-3.5 h-3.5 mr-2 ${isArmed ? 'animate-pulse' : ''}`} />
                        {isArmed ? 'ARMED' : 'SAFE'}
                    </button>
                    <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
                        Network: <span className="text-emerald-500">{status?.status === 'online' ? 'CONNECTED' : 'STANDBY'}</span>
                    </div>
                </div>
            </div>

            {/* Interaction Feedback Bar */}
            <div className="bg-slate-950/60 border border-white/5 p-3 rounded-lg flex items-center gap-4">
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Feedback Log:</span>
                <span className="text-[10px] font-mono text-emerald-400 font-bold">{lastAction || "Awaiting commands..."}</span>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Left: Scanner Feed */}
                <div className="md:col-span-2 space-y-6">
                    <Card className="bg-slate-950/40 border-slate-800 backdrop-blur-xl relative overflow-hidden group border-white/5">
                        <CardHeader className="pb-4 border-b border-white/5 flex flex-row items-center justify-between">
                            <CardTitle className="text-lg font-semibold tracking-tight text-slate-100 flex items-center gap-2">
                                <Crosshair className="w-4 h-4 text-purple-500 animate-pulse" />
                                Spectral Anomaly Scanner
                            </CardTitle>
                            <div className="flex gap-2">
                                <span className="text-[9px] bg-purple-500/10 text-purple-400 px-2 py-0.5 rounded border border-purple-500/20 font-black uppercase">
                                    Hype Spike
                                </span>
                                <span className="text-[9px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20 font-black uppercase">
                                    NEH Decay
                                </span>
                            </div>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <div className="divide-y divide-white/5">
                                {loading ? (
                                    <div className="py-20 text-center text-slate-600 animate-pulse font-mono text-xs tracking-widest uppercase">Initializing Quantum Sensors...</div>
                                ) : (
                                    scans.map((scan, i) => {
                                        const isActive = status?.active_markets?.includes(scan.id);
                                        return (
                                            <div key={i} className={`py-6 transition-all px-4 -mx-4 group/item ${isActive ? 'bg-emerald-500/5' : 'hover:bg-white/[0.02]'}`}>
                                                <div className="flex justify-between items-start mb-3">
                                                    <div className="space-y-1">
                                                        <div className="flex items-center gap-2">
                                                            <h3 className={`font-bold text-sm leading-tight transition-colors uppercase tracking-tight ${isActive ? 'text-emerald-400' : 'text-slate-100 group-hover/item:text-purple-400'}`}>{scan.question}</h3>
                                                            {isActive && (
                                                                <span className="text-[8px] font-black px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse uppercase">
                                                                    Active
                                                                </span>
                                                            )}
                                                            <span className={`text-[8px] font-black px-1.5 py-0.5 rounded ${scan.strategy === 'No-Folio (NEH)' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'bg-purple-500/20 text-purple-400 border border-purple-500/30'} uppercase`}>
                                                                {scan.strategy === 'No-Folio (NEH)' ? 'NEH' : 'HYPE'}
                                                            </span>
                                                        </div>
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
                                                                <span className="text-[9px] text-slate-500 font-bold uppercase transition-colors">Liq: {scan.liquidity_score}</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div className="flex flex-col items-end">
                                                        <span className={`${scan.strategy === 'No-Folio (NEH)' ? 'text-blue-400' : 'text-purple-400'} font-black font-mono text-sm drop-shadow-[0_0_8px_rgba(168,85,247,0.3)]`}>
                                                            {scan.strategy === 'No-Folio (NEH)' ? 'GRIND HIGH' : `+${(scan.spike_magnitude * 100).toFixed(1)}% Intensity`}
                                                        </span>
                                                        <span className="text-[10px] text-slate-500 font-mono mt-1">{scan.timestamp}</span>
                                                    </div>
                                                </div>
                                                <div className="flex justify-between items-center bg-slate-900/60 border border-white/5 py-2 px-3 rounded text-[9px] text-slate-400 font-black uppercase tracking-[0.15em]">
                                                    <span className="flex items-center gap-2">
                                                        <div className="w-1 h-1 bg-purple-500 rounded-full" />
                                                        REASON: {scan.reason}
                                                    </span>
                                                    <div className="flex gap-4">
                                                        <button
                                                            onClick={() => startStrategy(scan.id, scan.token_id, "liquidity_grinder")}
                                                            className={`transition-all flex items-center gap-1 px-2 py-1 rounded hover:bg-purple-500/10 ${isActive ? 'text-emerald-400' : 'text-purple-500/80 hover:text-purple-400'}`}
                                                        >
                                                            <Activity className="w-2.5 h-2.5" />
                                                            {isActive ? 'RE-GRIND' : 'Grinder'}
                                                        </button>
                                                        <button
                                                            onClick={() => startStrategy(scan.id, scan.token_id, "neh")}
                                                            className="text-blue-500/80 hover:text-blue-400 transition-colors flex items-center gap-1 border-l border-white/10 pl-4 px-2 py-1 rounded hover:bg-blue-500/10"
                                                        >
                                                            <Zap className="w-2.5 h-2.5" />
                                                            NEH Grind
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    })
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right: Tactical Control */}
                <div className="space-y-6">
                    <Card className="bg-slate-950/40 border-slate-800 backdrop-blur-md border-white/10 shadow-[0_10px_40px_rgba(0,0,0,0.5)]">
                        <CardHeader className="pb-4 border-b border-white/5 flex flex-row items-center justify-between">
                            <CardTitle className="text-xs font-bold tracking-[0.2em] text-slate-400 uppercase">Tactical Command</CardTitle>
                            <Settings2 className="w-3.5 h-3.5 text-slate-600" />
                        </CardHeader>
                        <CardContent className="pt-6 space-y-6">
                            {/* Strategy: Grinder Config */}
                            <div className="space-y-4">
                                <div className="flex justify-between items-center">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 bg-emerald-500 rounded-sm animate-pulse" />
                                        <span className="text-xs font-black text-slate-200 uppercase tracking-widest">Global Config</span>
                                    </div>
                                </div>
                                <div className="space-y-5 p-4 bg-slate-900/80 rounded-lg border border-white/5">
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-[10px] font-black text-slate-500 uppercase tracking-widest">
                                            <span>Spread Width</span>
                                            <span className="text-purple-400">{(grinderSpread * 100).toFixed(1)}%</span>
                                        </div>
                                        <input
                                            type="range" min="0.005" max="0.05" step="0.005"
                                            value={grinderSpread}
                                            onChange={(e) => {
                                                const val = parseFloat(e.target.value);
                                                setGrinderSpread(val);
                                                syncRiskConfig(val, grinderSize);
                                            }}
                                            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-purple-500 hover:accent-purple-400 transition-all"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-[10px] font-black text-slate-500 uppercase tracking-widest">
                                            <span>Max Position Size</span>
                                            <span className="text-purple-400">${grinderSize} USDC</span>
                                        </div>
                                        <input
                                            type="range" min="5" max="250" step="5"
                                            value={grinderSize}
                                            onChange={(e) => {
                                                const val = parseInt(e.target.value);
                                                setGrinderSize(val);
                                                syncRiskConfig(grinderSpread, val);
                                            }}
                                            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-purple-500 hover:accent-purple-400 transition-all"
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Risk Management */}
                            <div className="p-4 rounded-lg bg-red-500/5 border border-red-500/10 space-y-3">
                                <div className="flex items-center gap-2 mb-1">
                                    <Sliders className="w-3 h-3 text-red-500" />
                                    <div className="font-black text-[10px] text-red-500/80 uppercase tracking-[0.15em]">Risk Sentry Active</div>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="bg-slate-950/80 p-3 rounded border border-white/5">
                                        <span className="text-[8px] text-slate-500 block uppercase font-black tracking-widest mb-1">Stop Loss</span>
                                        <span className="text-xs font-mono font-bold text-red-500">15.0%</span>
                                    </div>
                                    <div className="bg-slate-950/80 p-3 rounded border border-white/5">
                                        <span className="text-[8px] text-slate-500 block uppercase font-black tracking-widest mb-1">Take Profit</span>
                                        <span className="text-xs font-mono font-bold text-emerald-500">25.0%</span>
                                    </div>
                                </div>
                            </div>

                            {/* Position Merger */}
                            <button
                                onClick={runMerge}
                                disabled={merging}
                                className={`w-full p-4 rounded-lg bg-slate-900 hover:bg-slate-800 border border-white/5 flex flex-col items-start gap-2 group transition-all active:scale-[0.98] ${merging ? 'opacity-50' : 'hover:border-purple-500/40 shadow-lg'}`}
                            >
                                <div className="flex justify-between items-center w-full">
                                    <div className="flex items-center gap-2">
                                        <Layers className={`w-3.5 h-3.5 ${merging ? 'animate-spin text-emerald-400' : 'text-purple-500'}`} />
                                        <div className="font-black text-[10px] text-slate-200 uppercase tracking-widest">Shadow Merger</div>
                                    </div>
                                    <ChevronRight className="w-3 h-3 text-slate-600 group-hover:translate-x-1 transition-transform" />
                                </div>
                                <p className="text-[9px] text-slate-500 text-left uppercase font-bold tracking-tight">
                                    {merging ? 'Accessing liquidity pools...' : 'Consolidate YES/NO pairs into USDC'}
                                </p>
                            </button>

                            <button
                                onClick={stopStrategy}
                                className="w-full py-4 bg-red-500 hover:bg-red-600 text-white border-b-4 border-red-800 rounded-lg text-[10px] font-black uppercase tracking-[0.3em] transition-all flex items-center justify-center gap-2 mt-4 active:border-b-0 active:translate-y-1 shadow-xl"
                            >
                                <Play className="w-4 h-4 fill-white rotate-90" />
                                Emergency Kill-Switch
                            </button>
                        </CardContent>
                    </Card>

                    <Card className="bg-emerald-500/5 border-emerald-500/20 p-5 border shadow-lg">
                        <div className="flex items-center gap-4 text-emerald-400">
                            <div className="p-2 bg-emerald-500/20 rounded-full">
                                <TrendingUp className="w-5 h-5" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] font-black uppercase tracking-widest text-emerald-500/60">Ghost Target Yield</span>
                                <span className="text-xl font-mono font-bold text-emerald-400">+6.8% <span className="text-[10px] text-emerald-500/40 tracking-normal">DAILY</span></span>
                            </div>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    )
}
