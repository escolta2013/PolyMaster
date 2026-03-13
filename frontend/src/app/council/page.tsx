"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Bot, BrainCircuit, ShieldAlert, MessageSquare, ExternalLink, Globe, Scale, TrendingUp, ChevronRight, Fingerprint, Network } from "lucide-react"

export default function CouncilPage() {
    const [feed, setFeed] = React.useState<any[]>([])
    const [status, setStatus] = React.useState<any>(null)
    const [loading, setLoading] = React.useState(true)
    const [selectedBrief, setSelectedBrief] = React.useState<any>(null)

    const fetchData = React.useCallback(async () => {
        try {
            const statusRes = await fetch("http://127.0.0.1:8000/council/status")
            const feedRes = await fetch("http://127.0.0.1:8000/council/feed")

            if (statusRes.ok) setStatus(await statusRes.json())
            if (feedRes.ok) setFeed(await feedRes.json())
        } catch (error) {
            console.error("Failed to fetch Council data", error)
        } finally {
            setLoading(false)
        }
    }, [])

    React.useEffect(() => {
        fetchData()
        const interval = setInterval(fetchData, 15000)
        return () => clearInterval(interval)
    }, [fetchData])

    return (
        <div className="container mx-auto px-6 py-10 space-y-8 max-w-7xl font-sans selection:bg-blue-500/30 bg-[#020617] text-slate-100 min-h-screen">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-8 relative">
                <div className="absolute -top-10 -left-10 w-60 h-60 bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />
                <div>
                    <h1 className="text-4xl font-black tracking-tighter text-slate-100 flex items-center gap-3">
                        <Bot className="w-9 h-9 text-blue-500 drop-shadow-[0_0_15px_rgba(59,130,246,0.5)]" />
                        THE COUNCIL
                        <span className="text-sm font-light text-slate-500 tracking-normal italic uppercase self-end mb-1">v3.0 Governance Swarm</span>
                    </h1>
                    <p className="text-slate-400 text-sm mt-2 font-medium flex items-center gap-2">
                        <Scale className="w-3 h-3 text-blue-400" />
                        Multi-Agent Protocol • {status?.governance || "Consensus Required"}
                    </p>
                </div>
                <div className="flex flex-col items-end gap-2 text-right">
                    <div className="px-5 py-2 bg-blue-950/30 border border-blue-500/20 rounded-full text-[10px] font-black text-blue-400 flex items-center tracking-widest uppercase backdrop-blur-md">
                        <div className="w-2 h-2 bg-blue-500 rounded-full mr-3 shadow-[0_0_10px_rgba(59,130,246,0.8)] animate-pulse" />
                        Neural Link: {status?.status || "Connecting..."}
                    </div>
                </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                {/* Left: Agent Status Monitor */}
                <div className="space-y-4">
                    <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-1">Active Swarm</h3>
                    {status?.active_agents?.map((agent: string) => (
                        <Card key={agent} className="bg-slate-900/40 border-white/5 hover:border-blue-500/20 transition-all group">
                            <CardContent className="p-4 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-slate-950 rounded-lg group-hover:bg-blue-500/10 transition-colors">
                                        <Bot className="w-3.5 h-3.5 text-blue-400" />
                                    </div>
                                    <div>
                                        <div className="font-black text-xs text-slate-200 tracking-tight">{agent}</div>
                                        <div className="text-[9px] text-slate-500 uppercase font-bold">Latency: 45ms</div>
                                    </div>
                                </div>
                                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full shadow-[0_0_5px_rgba(16,185,129,0.5)]"></div>
                            </CardContent>
                        </Card>
                    ))}
                    <div className="p-4 bg-slate-900/20 rounded-lg border border-dashed border-slate-800 flex flex-col items-center justify-center gap-2 opacity-50">
                        <Network className="w-4 h-4 text-slate-600" />
                        <span className="text-[8px] font-black uppercase tracking-tighter text-slate-600">Syncing Node #72</span>
                    </div>
                </div>

                {/* Center/Right: Consensus Feed */}
                <div className="md:col-span-3 space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
                            <BrainCircuit className="w-5 h-5 text-purple-400" />
                            Consensus Feed
                        </h2>
                        <div className="text-[10px] text-slate-500 font-mono flex items-center gap-2">
                            <span className="animate-pulse text-blue-500">●</span> LIVE STREAMING
                        </div>
                    </div>

                    <div className="grid gap-6">
                        {loading ? (
                            <div className="py-32 text-center text-slate-500 italic font-mono text-sm tracking-widest uppercase animate-pulse">Establishing Neural Consensus...</div>
                        ) : feed.length === 0 ? (
                            <div className="py-40 bg-slate-950/20 rounded-3xl border border-slate-900 flex flex-col items-center justify-center text-slate-600">
                                <ShieldAlert className="w-12 h-12 mb-4 opacity-20" />
                                <span className="font-mono text-xs uppercase tracking-widest">No signals requiring intervention.</span>
                            </div>
                        ) : (
                            feed.map((item, i) => (
                                <Card key={i} className="bg-slate-950/60 border-slate-800 hover:border-blue-500/30 transition-all relative overflow-hidden group">
                                    <div className={`absolute top-0 left-0 w-1 h-full ${item.consensus === "YES" ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                                    <CardContent className="p-6">
                                        <div className="flex justify-between items-start mb-4">
                                            <div className="space-y-1">
                                                <div className="flex items-center gap-3">
                                                    <span className={`text-[9px] font-black px-2 py-0.5 rounded-full ${item.consensus === "YES" ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'} uppercase tracking-widest`}>
                                                        {item.consensus === "YES" ? 'Consensus Reached' : 'Divergent Perspectives'}
                                                    </span>
                                                    <span className="text-[10px] text-slate-500 font-mono tracking-tighter uppercase">{item.timestamp.split('T')[1].split('.')[0]}</span>
                                                </div>
                                                <h3 className="text-lg font-black text-slate-100 group-hover:text-blue-400 transition-colors uppercase tracking-tight max-w-2xl leading-tight mt-2">
                                                    {item.market_name}
                                                </h3>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-2xl font-black text-slate-100 font-mono italic">
                                                    {Math.round(item.confidence * 100)}%
                                                </div>
                                                <div className="text-[9px] text-slate-500 uppercase font-black tracking-widest">Global Confidence</div>
                                            </div>
                                        </div>

                                        <div className="bg-slate-900/50 p-4 rounded-xl border border-white/5 mb-4 relative overflow-hidden">
                                            <div className="absolute top-0 right-0 p-3 opacity-10">
                                                <Fingerprint className="w-8 h-8" />
                                            </div>
                                            <p className="text-sm text-slate-300 font-medium leading-relaxed italic border-l-2 border-blue-500/30 pl-4">
                                                "{item.reasoning}"
                                            </p>
                                        </div>

                                        <div className="flex items-center justify-between mt-6 pt-6 border-t border-slate-800/50">
                                            <div className="flex gap-1 overflow-hidden">
                                                {item.agent_reports?.map((r: any, idx: number) => (
                                                    <div key={idx} className="w-1.5 h-1.5 bg-blue-500/40 rounded-full" title={r.agent} />
                                                )) || [1, 2, 3].map(d => <div key={d} className="w-1.5 h-1.5 bg-slate-800 rounded-full" />)}
                                                <span className="text-[9px] text-slate-500 uppercase font-black ml-2 tracking-widest">
                                                    {item.agent_reports?.length || 0} Agents Validated
                                                </span>
                                            </div>
                                            <button
                                                onClick={() => setSelectedBrief(item)}
                                                className="flex items-center gap-2 text-[10px] font-black text-blue-400 hover:text-blue-300 transition-colors uppercase tracking-[0.2em] group/btn"
                                            >
                                                View Detailed Brief
                                                <ChevronRight className="w-3 h-3 group-hover/btn:translate-x-1 transition-transform" />
                                            </button>
                                        </div>
                                    </CardContent>

                                    {/* Decorative subtle pulse for high confidence markets */}
                                    {item.confidence > 0.8 && (
                                        <div className="absolute top-2 right-2 w-1.5 h-1.5 bg-emerald-500 rounded-full animate-ping opacity-50" />
                                    )}
                                </Card>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* Detailed Brief Modal */}
            {selectedBrief && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-300">
                    <div
                        className="bg-slate-900 border border-blue-500/20 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="p-6 border-b border-white/5 bg-slate-950 flex justify-between items-center">
                            <div>
                                <h3 className="text-xs font-black text-blue-400 uppercase tracking-widest mb-1">Decomposed Consensus</h3>
                                <div className="text-lg font-black text-white uppercase tracking-tighter truncate max-w-md">{selectedBrief.market_name}</div>
                            </div>
                            <button
                                onClick={() => setSelectedBrief(null)}
                                className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-500"
                            >
                                <ChevronRight className="w-5 h-5 rotate-90" />
                            </button>
                        </div>
                        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto custom-scrollbar">
                            {selectedBrief.agent_reports?.map((report: any, idx: number) => (
                                <div key={idx} className="relative pl-6 border-l border-blue-500/20 py-2 group">
                                    <div className="absolute left-[-5px] top-6 w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.6)] group-hover:scale-125 transition-transform" />
                                    <div className="flex justify-between items-start mb-2">
                                        <span className="text-xs font-black text-slate-100 uppercase tracking-widest">{report.agent}</span>
                                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 ${report.confidence > 0.6 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                            CONF: {Math.round(report.confidence * 100)}%
                                        </span>
                                    </div>
                                    <p className="text-sm text-slate-400 leading-relaxed font-medium italic">
                                        "{report.reasoning}"
                                    </p>
                                </div>
                            ))}
                        </div>
                        <div className="p-6 bg-slate-950/40 border-t border-white/5 flex gap-4">
                            <div className="flex-1 p-4 rounded-xl bg-blue-500/5 border border-blue-500/10">
                                <span className="text-[9px] font-black text-blue-500 uppercase block mb-1">AGGREGATE SCORE</span>
                                <span className="text-2xl font-black text-white font-mono">{Math.round(selectedBrief.confidence * 100)}%</span>
                            </div>
                            <div className="flex-1 p-4 rounded-xl bg-purple-500/5 border border-purple-500/10">
                                <span className="text-[9px] font-black text-purple-500 uppercase block mb-1">INTENSITY SPIKE</span>
                                <span className="text-2xl font-black text-white font-mono">{(selectedBrief.intensity_score * 100).toFixed(1)}%</span>
                            </div>
                        </div>
                    </div>
                    <div className="absolute inset-0 -z-10" onClick={() => setSelectedBrief(null)} />
                </div>
            )}
        </div>
    )
}
