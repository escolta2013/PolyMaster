"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Shield, TrendingUp, Award, ExternalLink, RefreshCw, Briefcase, Zap, Search } from "lucide-react"

interface Wallet {
    address: string
    grade: string
    roi: number
    win_rate: number
    total_trades: number
    profit_usdc: number
    volume_usdc: number
    last_updated: string
}

export function SmartMoneyWallets() {
    const [wallets, setWallets] = React.useState<Wallet[]>([])
    const [loading, setLoading] = React.useState(true)
    const [syncing, setSyncing] = React.useState(false)

    const fetchData = async () => {
        setLoading(true)
        try {
            // Updated to use the refined wallets endpoint
            const res = await fetch("http://127.0.0.1:8000/tracker/wallets?sort_by=roi&limit=25")
            if (res.ok) {
                const data = await res.json()
                setWallets(data || [])
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
            const res = await fetch("http://127.0.0.1:8000/tracker/sync", { method: 'POST' })
            if (res.ok) {
                await fetchData()
            }
        } catch (error) {
            console.error("Sync failed", error)
        } finally {
            setSyncing(false)
        }
    }

    React.useEffect(() => {
        fetchData()
    }, [])

    const getGradeStyle = (grade: string) => {
        switch (grade) {
            case 'WHALE':
                return "bg-purple-500/10 text-purple-400 border-purple-500/20"
            case 'SHARK':
                return "bg-blue-500/10 text-blue-400 border-blue-500/20"
            case 'ORCA':
                return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
            default:
                return "bg-slate-500/10 text-slate-400 border-slate-500/20"
        }
    }

    return (
        <Card className="w-full mt-8 bg-slate-950/40 border-slate-800 backdrop-blur-md">
            <CardHeader className="pb-4 border-b border-slate-800/50">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-semibold tracking-tight flex items-center gap-2 text-slate-100">
                        <Shield className="w-4 h-4 text-emerald-500" />
                        <span>Institutional Wallet Intelligence</span>
                    </CardTitle>
                    <button
                        onClick={handleSync}
                        disabled={syncing}
                        className="flex items-center gap-2 bg-slate-800/40 hover:bg-slate-700/60 text-[10px] uppercase font-bold tracking-widest px-4 py-2 rounded-md border border-slate-700/50 transition-all active:scale-95 disabled:opacity-50 text-slate-300"
                    >
                        <RefreshCw className={`w-3 h-3 ${syncing ? 'animate-spin' : ''}`} />
                        <span>{syncing ? 'Re-Indexing Networks...' : 'Synchronize Database'}</span>
                    </button>
                </div>
            </CardHeader>
            <CardContent className="pt-6">
                <div className="rounded-lg border border-slate-800 overflow-hidden bg-slate-950/20">
                    <table className="w-full text-xs text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-900/50 text-slate-500 border-b border-slate-800 uppercase tracking-widest font-bold">
                                <th className="px-6 py-4">Identification</th>
                                <th className="px-6 py-4 text-center">Tier Status</th>
                                <th className="px-6 py-4 text-right">ROI Alpha</th>
                                <th className="px-6 py-4 text-right">Win Frequency</th>
                                <th className="px-6 py-4 text-right">Aggregate Volume</th>
                                <th className="px-6 py-4 text-right">Net Profit</th>
                                <th className="px-6 py-4 text-center">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {loading ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-12 text-center text-slate-400 font-medium font-mono uppercase tracking-[0.2em]">
                                        Retrieving Classified Signatures...
                                    </td>
                                </tr>
                            ) : wallets.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-12 text-center text-slate-500 italic">
                                        No high-probability signatures identified in the last scan cycle.
                                    </td>
                                </tr>
                            ) : (
                                wallets.map((wallet) => (
                                    <tr key={wallet.address} className="hover:bg-slate-800/40 transition-all duration-200 group">
                                        <td className="px-6 py-4 font-mono text-xs text-slate-300">
                                            <div className="flex items-center gap-2 capitalize">
                                                <Search className="w-3 h-3 text-slate-600" />
                                                {wallet.address.slice(0, 8)}...{wallet.address.slice(-6)}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <span className={`px-2.5 py-1 rounded border text-[9px] font-black tracking-tighter uppercase ${getGradeStyle(wallet.grade)}`}>
                                                {wallet.grade}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-emerald-400 font-bold text-sm">
                                            +{(wallet.roi * 100).toFixed(1)}%
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-slate-400">
                                            {(wallet.win_rate * 100).toFixed(0)}%
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-slate-300">
                                            ${(wallet.volume_usdc || 0).toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono font-bold text-slate-100">
                                            ${wallet.profit_usdc.toLocaleString()}
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
    )
}
