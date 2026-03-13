"use client"

import * as React from "react"
import { X, Zap, ShieldCheck, AlertTriangle, DollarSign, Crosshair, Target } from "lucide-react"
import { ClusterAlert } from "@/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

interface CopyTradeModalProps {
    isOpen: boolean
    onClose: () => void
    alert?: ClusterAlert
}

export function CopyTradeModal({ isOpen, onClose, alert }: CopyTradeModalProps) {
    const [sizeUsdc, setSizeUsdc] = React.useState(100)
    const [price, setPrice] = React.useState(0.5)
    const [loading, setLoading] = React.useState(false)
    const [result, setResult] = React.useState<any>(null)
    const [status, setStatus] = React.useState<any>(null)

    React.useEffect(() => {
        if (!isOpen) {
            setResult(null)
            return
        }
        fetch(`${API_URL}/tracker/copy/status`)
            .then(r => r.json())
            .then(setStatus)
            .catch(() => { })
    }, [isOpen])

    if (!isOpen || !alert) return null

    const handleCopy = async () => {
        setLoading(true)
        setResult(null)
        try {
            const res = await fetch(`${API_URL}/tracker/copy`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    source_wallet: "cluster_signal",
                    token_id: alert.token_id,
                    market_id: alert.market_id,
                    market_question: alert.market_question,
                    outcome: alert.outcome,
                    price,
                    size_usdc: sizeUsdc,
                }),
            })
            const data = await res.json()
            setResult(data)
        } catch (err) {
            setResult({ status: "error", message: "Network connection failure during execution." })
        } finally {
            setLoading(false)
        }
    }

    return (
        <div
            className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-md animate-in fade-in duration-300"
            onClick={onClose}
        >
            <div
                className="w-full max-w-lg bg-slate-900 border border-white/10 rounded-2xl shadow-3xl relative overflow-hidden animate-in zoom-in-95 duration-200"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Ambient glow */}
                <div className="absolute -top-20 -right-20 w-40 h-40 bg-emerald-500/10 rounded-full blur-[80px] pointer-events-none" />

                {/* Header */}
                <div className="flex items-center justify-between p-8 border-b border-white/5 relative">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-white text-slate-950 rounded-lg flex items-center justify-center shadow-lg">
                            <Zap className="w-6 h-6" />
                        </div>
                        <div>
                            <h3 className="text-lg font-black text-slate-100 uppercase tracking-tighter">Execute Vector SYNK</h3>
                            <div className="flex items-center gap-2 mt-1">
                                <div className={`w-1.5 h-1.5 rounded-full ${status?.simulation ? 'bg-yellow-500' : 'bg-emerald-500'} animate-pulse`} />
                                <p className="text-[10px] text-slate-500 font-bold tracking-widest uppercase">
                                    {status?.simulation ? "Simulation Engine Active" : "Production Node Live"}
                                </p>
                            </div>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors p-2">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-8 space-y-6">
                    {/* Market info */}
                    <div className="p-5 bg-slate-950/60 rounded-xl border border-white/5">
                        <p className="text-sm font-black text-slate-100 leading-tight uppercase tracking-tighter">{alert.market_question}</p>
                        <div className="flex items-center gap-4 mt-4">
                            <span className={`px-2.5 py-0.5 rounded text-[9px] font-black uppercase border ${alert.outcome === "YES"
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : "bg-red-500/10 text-red-500 border-red-500/20"
                                }`}>
                                POSITION: {alert.outcome}
                            </span>
                            <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">
                                {alert.wallet_count} NODES IN CLUSTER
                            </span>
                        </div>
                    </div>

                    {/* Controls */}
                    <div className="grid grid-cols-2 gap-6">
                        <div className="space-y-3">
                            <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2">
                                <Target className="w-3 h-3" /> Target Price
                            </label>
                            <input
                                type="number"
                                step={0.01}
                                min={0.01}
                                max={0.99}
                                value={price}
                                onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
                                className="w-full px-4 py-3 bg-slate-950 border border-white/10 rounded-lg text-sm font-black font-mono text-emerald-400 focus:border-emerald-500/50 focus:outline-none transition-colors"
                            />
                        </div>
                        <div className="space-y-3">
                            <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2">
                                <DollarSign className="w-3 h-3" /> Alloc (USDC)
                            </label>
                            <input
                                type="number"
                                step={10}
                                min={5}
                                max={status?.max_per_trade || 500}
                                value={sizeUsdc}
                                onChange={(e) => setSizeUsdc(parseInt(e.target.value) || 0)}
                                className="w-full px-4 py-3 bg-slate-950 border border-white/10 rounded-lg text-sm font-black font-mono text-slate-100 focus:border-emerald-500/50 focus:outline-none transition-colors"
                            />
                        </div>
                    </div>

                    {/* Safety info */}
                    {status && (
                        <div className="flex items-center justify-between px-1">
                            <div className="flex items-center gap-4 text-[9px] text-slate-500 font-black uppercase tracking-widest">
                                <span className="flex items-center gap-1.5">
                                    <ShieldCheck className="w-3.5 h-3.5 text-blue-500" />
                                    Risk Limit: ${status.max_per_trade}
                                </span>
                            </div>
                            <span className="text-[9px] text-slate-500 font-black tracking-widest uppercase">
                                Available: ${status.remaining_today}
                            </span>
                        </div>
                    )}

                    {/* Result */}
                    {result && (
                        <div className={`p-4 rounded-xl border text-sm animate-in slide-in-from-top-2 duration-300 ${result.status === "error"
                            ? "bg-red-500/10 border-red-500/20 text-red-400"
                            : result.status === "simulated"
                                ? "bg-yellow-500/10 border-yellow-500/20 text-yellow-500"
                                : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                            }`}>
                            <div className="flex items-center gap-2 mb-2">
                                <span className="font-black uppercase text-[10px] tracking-[0.2em]">{result.status} SIGNATURE</span>
                            </div>
                            <p className="text-xs leading-relaxed font-bold opacity-90 uppercase tracking-tighter">{result.message}</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-8 pt-0">
                    <button
                        onClick={handleCopy}
                        disabled={loading || price <= 0 || price >= 1 || sizeUsdc < 5}
                        className="w-full py-5 bg-white hover:brightness-110 text-slate-950 rounded-xl font-black text-xs uppercase tracking-[0.3em] transition-all flex items-center justify-center gap-3 transform hover:scale-[1.01] active:scale-95 disabled:opacity-20 disabled:cursor-not-allowed shadow-2xl"
                    >
                        <Zap className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        {loading ? 'EXECUTING TRANSACTION…' : status?.simulation ? 'STANCE: SIMULATION' : 'STANCE: LIVE EXECUTION'}
                    </button>
                </div>
            </div>
        </div>
    )
}

function Target({ className }: { className?: string }) {
    return <Crosshair className={className} />
}
