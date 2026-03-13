"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Shield, ExternalLink, RefreshCw, Briefcase, Zap, Search } from "lucide-react"
import { Wallet } from "@/types"

// Elegant currency formatter
function formatCurrency(num: number, compact = false) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        notation: compact ? "compact" : "standard",
        maximumFractionDigits: compact ? 1 : 0
    }).format(num);
}

interface SmartMoneyWalletsProps {
    initialWallets: Wallet[];
}

export function SmartMoneyWallets({ initialWallets }: SmartMoneyWalletsProps) {
    const [wallets, setWallets] = React.useState<Wallet[]>(initialWallets)
    const [loading, setLoading] = React.useState(false)
    const [syncing, setSyncing] = React.useState(false)
    const [selectedWallet, setSelectedWallet] = React.useState<Wallet | null>(null)

    const fetchData = async () => {
        setLoading(true)
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/tracker/wallets?sort_by=roi&limit=25`)
            if (res.ok) {
                const data = await res.json()
                setWallets(data.wallets || data || [])
            }
        } catch (error) {
            console.error("Failed to fetch smart money", error)
        } finally {
            setLoading(false)
        }
    }

    const handleSync = async () => {
        setSyncing(true)
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/tracker/sync`, { method: 'POST' })
            if (res.ok) {
                await fetchData()
            }
        } catch (error) {
            console.error("Sync failed", error)
        } finally {
            setSyncing(false)
        }
    }

    const getGradeStyle = (grade: string) => {
        switch (grade) {
            case 'WHALE': return "bg-purple-500/10 text-purple-400 border-purple-500/20"
            case 'SHARK': return "bg-blue-500/10 text-blue-400 border-blue-500/20"
            case 'ORCA': return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
            default: return "bg-slate-500/10 text-slate-400 border-slate-500/20"
        }
    }

    return (
        <>
            <Card className="w-full bg-slate-950/40 border-slate-800 backdrop-blur-md shadow-2xl">
                <CardHeader className="pb-4 border-b border-white/5">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-lg font-bold tracking-tighter flex items-center gap-2 text-slate-100 uppercase">
                            <Shield className="w-4 h-4 text-emerald-500" />
                            <span>Institutional Wallet Intelligence</span>
                        </CardTitle>
                        <div className="flex flex-col items-end gap-2">
                            <button
                                onClick={handleSync}
                                disabled={syncing}
                                className="flex items-center gap-2 bg-slate-100 hover:bg-white text-slate-950 text-[10px] uppercase font-black tracking-widest px-4 py-2 rounded border border-transparent transition-all active:scale-95 disabled:opacity-50 shadow-[0_0_15px_rgba(255,255,255,0.1)]"
                            >
                                <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
                                <span>{syncing ? 'Indexing Networks...' : 'Re-Synchronize Nodes'}</span>
                            </button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="pt-6">
                    <div className="rounded border border-white/5 overflow-hidden bg-slate-950/20">
                        <table className="w-full text-xs text-left border-collapse">
                            <thead>
                                <tr className="bg-slate-900/50 text-slate-500 border-b border-white/5 uppercase tracking-widest font-black">
                                    <th className="px-6 py-4">Identification</th>
                                    <th className="px-6 py-4 text-center">Tier Status</th>
                                    <th className="px-6 py-4 text-right">ROI Alpha</th>
                                    <th className="px-6 py-4 text-right">Win Rate</th>
                                    <th className="px-6 py-4 text-right">Aggregate Volume</th>
                                    <th className="px-6 py-4 text-right">Net Profit</th>
                                    <th className="px-6 py-4 text-center">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {loading && wallets.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="px-6 py-12 text-center text-slate-400 font-medium font-mono uppercase tracking-[0.2em]">
                                            Retrieving Classified Signatures...
                                        </td>
                                    </tr>
                                ) : wallets.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="px-6 py-12 text-center text-slate-500 italic">
                                            No high-probability signatures identified.
                                        </td>
                                    </tr>
                                ) : (
                                    wallets.map((wallet) => (
                                        <tr
                                            key={wallet.address}
                                            onClick={() => setSelectedWallet(wallet)}
                                            className="hover:bg-white/5 transition-all duration-200 group cursor-pointer"
                                        >
                                            <td className="px-6 py-4 font-mono text-xs text-slate-300">
                                                <div className="flex items-center gap-2">
                                                    <Search className="w-3 h-3 text-slate-600 group-hover:text-emerald-500 transition-colors" />
                                                    {wallet.address.slice(0, 10)}...{wallet.address.slice(-6)}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-center">
                                                <span className={`px-3 py-1 rounded border text-[9px] font-black tracking-tighter uppercase whitespace-nowrap ${getGradeStyle(wallet.grade)}`}>
                                                    {wallet.grade}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-right font-mono text-emerald-400 font-black text-sm">
                                                +{(wallet.roi * 100).toFixed(1)}%
                                            </td>
                                            <td className="px-6 py-4 text-right font-mono text-slate-400">
                                                {(wallet.win_rate * 100).toFixed(0)}%
                                            </td>
                                            <td className="px-6 py-4 text-right font-mono text-slate-300">
                                                {formatCurrency(wallet.volume_usdc || 0, true)}
                                            </td>
                                            <td className="px-6 py-4 text-right font-mono font-bold text-slate-100">
                                                {formatCurrency(wallet.profit_usdc || 0, true)}
                                            </td>
                                            <td className="px-6 py-4 text-center">
                                                <div className="flex items-center justify-center gap-2">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                                                    <span className="text-[9px] text-slate-500 uppercase font-black tracking-wider">Active</span>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>

            {/* Wallet Detail Modal */}
            {selectedWallet && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-md" onClick={() => setSelectedWallet(null)}>
                    <div
                        className="w-full max-w-2xl bg-slate-900 border border-white/10 rounded-xl shadow-2xl p-8 relative animate-in fade-in zoom-in duration-200"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <button
                            onClick={() => setSelectedWallet(null)}
                            className="absolute top-6 right-6 text-slate-500 hover:text-white transition-colors p-2"
                        >
                            ✕
                        </button>

                        <div className="flex items-center gap-6 mb-8">
                            <div className={`w-16 h-16 rounded-full flex items-center justify-center ${getGradeStyle(selectedWallet.grade)} border-2`}>
                                <Shield className="w-8 h-8" />
                            </div>
                            <div>
                                <h3 className="text-2xl font-black text-slate-100 font-mono tracking-tighter">{selectedWallet.address}</h3>
                                <div className="flex items-center gap-3 mt-2">
                                    <span className={`px-3 py-1 rounded text-[10px] font-black uppercase tracking-widest border ${getGradeStyle(selectedWallet.grade)}`}>
                                        {selectedWallet.grade} TIER
                                    </span>
                                    <span className="text-slate-500 text-xs font-bold uppercase tracking-widest">
                                        Last Updated: {new Date(selectedWallet.last_updated).toLocaleDateString()}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-8">
                            <KPIBox label="Total PnL" value={formatCurrency(selectedWallet.profit_usdc || 0, selectedWallet.profit_usdc > 99999)} color="text-emerald-400" />
                            <KPIBox label="ROI Alpha" value={`+${(selectedWallet.roi * 100).toFixed(1)}%`} color="text-emerald-500" />
                            <KPIBox label="Win Rate" value={`${(selectedWallet.win_rate * 100).toFixed(0)}%`} color="text-blue-400" />
                            <KPIBox label="Volume" value={formatCurrency(selectedWallet.volume_usdc || 0, true)} color="text-slate-200" />
                        </div>

                        <div className="flex gap-4">
                            <ExternalButton href={`https://polygonscan.com/address/${selectedWallet.address}`} icon={<ExternalLink className="w-4 h-4" />} label="PolygonScan" />
                            <ExternalButton href={`https://polymarket.com/profile/${selectedWallet.address}`} icon={<Briefcase className="w-4 h-4" />} label="Polymarket Profile" color="bg-blue-600/10 text-blue-400 border-blue-500/30" />
                        </div>
                        <button
                            className="w-full mt-4 flex items-center justify-center gap-3 py-4 bg-emerald-500 hover:bg-emerald-400 text-slate-950 rounded-lg font-black text-xs uppercase tracking-[0.3em] transition-all transform hover:scale-[1.01] active:scale-95 shadow-[0_10px_30px_rgba(16,185,129,0.2)]"
                        >
                            <Zap className="w-4 h-4" />
                            Deploy Copy Trade Bot
                        </button>
                    </div>
                </div>
            )}
        </>
    )
}

function KPIBox({ label, value, color }: { label: string, value: string, color: string }) {
    return (
        <div className="bg-slate-950/60 p-5 rounded-lg border border-white/5">
            <div className="text-[9px] uppercase font-black text-slate-500 tracking-[0.2em] mb-2">{label}</div>
            <div className={`text-xl font-black font-mono tracking-tighter ${color}`}>{value}</div>
        </div>
    )
}

function ExternalButton({ href, icon, label, color = "bg-slate-800/50 text-slate-300 border-white/5" }: any) {
    return (
        <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className={`flex-1 flex items-center justify-center gap-3 py-4 ${color} border rounded-lg font-bold transition-all text-xs uppercase tracking-widest hover:brightness-125`}
        >
            {icon}
            {label}
        </a>
    )
}
