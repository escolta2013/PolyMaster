"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Bot, BrainCircuit, ShieldAlert, MessageSquare, ExternalLink, Globe } from "lucide-react"

export default function CouncilPage() {
    const [feed, setFeed] = React.useState<any[]>([])
    const [status, setStatus] = React.useState<any>(null)
    const [loading, setLoading] = React.useState(true)

    React.useEffect(() => {
        async function fetchData() {
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
        }
        fetchData()
        const interval = setInterval(fetchData, 15000)
        return () => clearInterval(interval)
    }, [])

    return (
        <div className="container mx-auto px-6 py-10 space-y-8 max-w-7xl font-sans selection:bg-blue-500/30">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-8 relative">
                <div className="absolute -top-10 -left-10 w-40 h-40 bg-blue-500/10 rounded-full blur-[100px] pointer-events-none" />
                <div>
                    <h1 className="text-4xl font-black tracking-tighter text-slate-100 flex items-center gap-3">
                        <Bot className="w-8 h-8 text-blue-500" />
                        THE COUNCIL
                        <span className="text-sm font-light text-slate-500 tracking-normal italic uppercase self-end mb-1">AI Swarm</span>
                    </h1>
                    <p className="text-slate-400 text-sm mt-2 font-medium">
                        Autonomous Governance & Signal Validation
                    </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                    <div className="px-4 py-1.5 bg-blue-500/5 border border-blue-500/20 rounded-sm text-[10px] font-black text-blue-400 flex items-center tracking-widest uppercase">
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-3 shadow-[0_0_8px_rgba(59,130,246,0.5)] animate-pulse" />
                        Agents: {status?.status || "Connecting..."}
                    </div>
                </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                {/* Left: Agent Status */}
                <div className="space-y-4">
                    <AgentStatusCard name="FedWatcher" role="Macro Analysis" status="Online" />
                    <AgentStatusCard name="RuleLawyer" role="Contract Audit" status="Online" />
                    <AgentStatusCard name="SentimentSwarm" role="Fake News Filter" status="Scanning" />
                </div>

                {/* Right: Intelligence Feed */}
                <div className="md:col-span-3">
                    <Card className="bg-slate-950/40 border-slate-800 backdrop-blur-md min-h-[500px]">
                        <CardHeader className="pb-4 border-b border-slate-800/50">
                            <CardTitle className="text-lg font-semibold tracking-tight text-slate-100 flex items-center gap-2">
                                <MessageSquare className="w-4 h-4 text-blue-400" />
                                Intelligence Feed
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-6">
                            <div className="space-y-6">
                                {loading ? (
                                    <div className="text-center text-slate-500 italic">Establishing neural link...</div>
                                ) : feed.length === 0 ? (
                                    <div className="text-center text-slate-500">No signals requiring attention.</div>
                                ) : (
                                    feed.map((item, i) => (
                                        <div key={i} className="flex gap-4 p-4 rounded-lg bg-slate-900/30 border border-slate-800/50 hover:border-blue-500/20 transition-colors">
                                            <div className="mt-1">
                                                {item.agent === "FedWatcher" && <BrainCircuit className="w-5 h-5 text-purple-400" />}
                                                {item.agent === "RuleLawyer" && <ShieldAlert className="w-5 h-5 text-yellow-400" />}
                                                {item.agent === "SentimentSwarm" && <Bot className="w-5 h-5 text-blue-400" />}
                                            </div>
                                            <div className="flex-1">
                                                <div className="flex justify-between items-center mb-1">
                                                    <span className="font-bold text-sm text-slate-200 uppercase tracking-tighter">{item.agent}</span>
                                                    <span className="text-[10px] text-slate-500 uppercase tracking-wider">{item.timestamp}</span>
                                                </div>
                                                <p className="text-sm text-slate-100 font-medium leading-relaxed mb-1">{item.content}</p>

                                                {item.metadata && (
                                                    <div className="mb-3 p-2 bg-slate-950/50 rounded border border-white/5 space-y-1">
                                                        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest flex items-center gap-1">
                                                            <Globe className="w-2.5 h-2.5" />
                                                            Ref: {item.metadata.original_title}
                                                        </div>
                                                        <a
                                                            href={item.metadata.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-[9px] text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors uppercase font-black"
                                                        >
                                                            Source: {item.metadata.source}
                                                            <ExternalLink className="w-2 h-2" />
                                                        </a>
                                                    </div>
                                                )}

                                                <div className="flex items-center gap-2">
                                                    <div className="h-1 w-24 bg-slate-800 rounded-full overflow-hidden">
                                                        <div className="h-full bg-emerald-500" style={{ width: `${item.confidence * 100}%` }}></div>
                                                    </div>
                                                    <span className="text-[10px] font-mono text-emerald-500">{Math.round(item.confidence * 100)}% Confidence</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}

function AgentStatusCard({ name, role, status }: any) {
    return (
        <Card className="bg-slate-900/20 border-white/5">
            <CardContent className="p-4 flex items-center justify-between">
                <div>
                    <div className="font-bold text-xs text-slate-300">{name}</div>
                    <div className="text-[10px] text-slate-500">{role}</div>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${status === 'Online' ? 'bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]' : 'bg-blue-500 animate-pulse'}`}></div>
                    <span className="text-[9px] uppercase font-bold text-slate-400">{status}</span>
                </div>
            </CardContent>
        </Card>
    )
}
