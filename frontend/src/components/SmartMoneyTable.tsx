"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { TrendingUp, Users, Activity, ExternalLink } from "lucide-react"

interface Market {
    id: string
    title: string
    volume: number
    liquidity: number
    outcomes: string // JSON string in current API mock, simplified for MVP
}

export function SmartMoneyTable() {
    const [markets, setMarkets] = React.useState<any[]>([])
    const [loading, setLoading] = React.useState(true)

    React.useEffect(() => {
        async function fetchData() {
            try {
                // Fetch from our FastAPI Backend
                const res = await fetch("http://127.0.0.1:8000/tracker/top-markets")
                if (res.ok) {
                    const data = await res.json()
                    setMarkets(data.markets || [])
                }
            } catch (error) {
                console.error("Failed to fetch markets", error)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [])

    return (
        <Card className="w-full">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-xl flex items-center space-x-2">
                        <Activity className="w-5 h-5 text-primary" />
                        <span>Live Market Activity</span>
                    </CardTitle>
                    <div className="text-sm text-muted-foreground">
                        Scanning {markets.length} active markets
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="rounded-md border border-white/10 overflow-hidden">
                    <table className="w-full text-sm text-left">
                        <thead className="text-xs uppercase bg-white/5 text-muted-foreground">
                            <tr>
                                <th className="px-6 py-3">Market</th>
                                <th className="px-6 py-3 text-right">Volume</th>
                                <th className="px-6 py-3 text-right">Liquidity</th>
                                <th className="px-6 py-3 text-center">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {loading ? (
                                <tr>
                                    <td colSpan={4} className="px-6 py-8 text-center text-muted-foreground">
                                        Connecting to Polymarket Data Feed...
                                    </td>
                                </tr>
                            ) : markets.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="px-6 py-8 text-center text-muted-foreground">
                                        No active volume spikes detected.
                                    </td>
                                </tr>
                            ) : (
                                markets.map((market) => (
                                    <tr key={market.id || Math.random()} className="bg-black/20 hover:bg-white/5 transition-colors">
                                        <td className="px-6 py-4 font-medium max-w-md truncate">
                                            {market.question || "Unknown Market"}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-emerald-400">
                                            ${market.volume?.toLocaleString() ?? 0}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-blue-400">
                                            ${market.liquidity?.toLocaleString() ?? 0}
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <button className="text-xs bg-primary/20 hover:bg-primary/40 text-primary px-2 py-1 rounded transition-colors flex items-center justify-center mx-auto space-x-1">
                                                <span>Analyze</span>
                                                <ExternalLink className="w-3 h-3" />
                                            </button>
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
