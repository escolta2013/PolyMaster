"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Shield, TrendingUp, Award, ExternalLink, RefreshCw } from "lucide-react"

interface Wallet {
    address: string
    grade: string
    roi: number
    win_rate: number
    total_trades: number
    profit_usdc: number
    last_updated: string
}

export function SmartMoneyWallets() {
    const [wallets, setWallets] = React.useState<Wallet[]>([])
    const [loading, setLoading] = React.useState(true)
    const [syncing, setSyncing] = React.useState(false)

    const fetchData = async () => {
        setLoading(true)
        try {
            const res = await fetch("http://127.0.0.1:8000/tracker/smart-money")
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

    return (
        <Card className="w-full mt-8">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-xl flex items-center space-x-2">
                        <Award className="w-5 h-5 text-yellow-400" />
                        <span>Smart Money Intelligence</span>
                    </CardTitle>
                    <button
                        onClick={handleSync}
                        disabled={syncing}
                        className="flex items-center space-x-2 bg-white/5 hover:bg-white/10 text-xs px-3 py-1.5 rounded-full border border-white/10 transition-all active:scale-95 disabled:opacity-50"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
                        <span>{syncing ? 'Analyzing Markets...' : 'Refresh Scan'}</span>
                    </button>
                </div>
            </CardHeader>
            <CardContent>
                <div className="rounded-md border border-white/10 overflow-hidden bg-black/40">
                    <table className="w-full text-sm text-left">
                        <thead className="text-xs uppercase bg-white/5 text-muted-foreground font-bold">
                            <tr>
                                <th className="px-6 py-4">Wallet Address</th>
                                <th className="px-6 py-4 text-center">Grade</th>
                                <th className="px-6 py-4 text-right">ROI</th>
                                <th className="px-6 py-4 text-right">Win Rate</th>
                                <th className="px-6 py-4 text-right">Profit (USDC)</th>
                                <th className="px-6 py-4 text-center">Protocol</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {loading ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center text-muted-foreground">
                                        Querying Smart Money DB...
                                    </td>
                                </tr>
                            ) : wallets.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center text-muted-foreground italic">
                                        No whale signatures detected yet. Run a Refresh Scan.
                                    </td>
                                </tr>
                            ) : (
                                wallets.map((wallet) => (
                                    <tr key={wallet.address} className="hover:bg-white/5 transition-colors group">
                                        <td className="px-6 py-4 font-mono text-xs text-blue-300">
                                            {wallet.address.slice(0, 6)}...{wallet.address.slice(-4)}
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${wallet.grade === 'A' ? 'bg-emerald-500/20 text-emerald-400' :
                                                    wallet.grade === 'B' ? 'bg-blue-500/20 text-blue-400' :
                                                        'bg-zinc-500/20 text-zinc-400'
                                                }`}>
                                                TIER {wallet.grade}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-emerald-400">
                                            +{(wallet.roi * 100).toFixed(1)}%
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-purple-400">
                                            {(wallet.win_rate * 100).toFixed(0)}%
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono font-bold">
                                            ${wallet.profit_usdc.toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <div className="flex items-center justify-center space-x-2">
                                                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                                                <span className="text-[10px] text-muted-foreground uppercase tracking-widest">Polymarket</span>
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
