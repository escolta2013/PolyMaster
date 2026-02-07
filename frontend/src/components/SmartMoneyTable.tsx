"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { TrendingUp, Activity, ExternalLink, BarChart3, Layers } from "lucide-react"

function formatCurrency(num: number) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        notation: 'compact',
        maximumFractionDigits: 1
    }).format(num);
}

export function SmartMoneyTable() {
    const [markets, setMarkets] = React.useState<any[]>([])
    const [loading, setLoading] = React.useState(true)
    const [limit, setLimit] = React.useState(10)

    React.useEffect(() => {
        async function fetchData() {
            setLoading(true)
            try {
                const res = await fetch(`http://127.0.0.1:8000/tracker/top-markets?limit=${limit}`)
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
    }, [limit])

    return (
        <Card className="w-full bg-slate-950/40 border-slate-800 backdrop-blur-md">
            <CardHeader className="pb-4 border-b border-slate-800/50">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-semibold tracking-tight flex items-center gap-2 text-slate-100">
                        <Activity className="w-4 h-4 text-emerald-500" />
                        <span>High-Velocity Market Clusters</span>
                    </CardTitle>
                    <div className="flex items-center gap-3">
                        <select
                            value={limit}
                            onChange={(e) => setLimit(Number(e.target.value))}
                            className="bg-slate-900 border border-slate-700 text-slate-300 text-[10px] uppercase font-bold px-2 py-1 rounded outline-none focus:border-emerald-500/50"
                        >
                            <option value={10}>10</option>
                            <option value={25}>25</option>
                            <option value={50}>50</option>
                        </select>
                        <div className="px-3 py-1 bg-slate-800/50 rounded-full text-[10px] font-medium text-slate-400 uppercase tracking-widest border border-slate-700/50">
                            Monitoring {markets.length} active vectors
                        </div>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="pt-6">
                <div className="rounded-lg border border-slate-800 overflow-hidden bg-slate-950/20">
                    <table className="w-full text-xs text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-900/50 text-slate-500 border-b border-slate-800 uppercase tracking-widest font-bold">
                                <th className="px-6 py-4 font-bold">Market Vector</th>
                                <th className="px-6 py-4 text-right">Volume (USDC)</th>
                                <th className="px-6 py-4 text-right">Liquidity Delta</th>
                                <th className="px-6 py-4 text-center">Protocol Link</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {loading ? (
                                <tr>
                                    <td colSpan={4} className="px-6 py-12 text-center text-slate-400 font-medium">
                                        <div className="flex items-center justify-center gap-3">
                                            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                                            Scanning Vector Field (Depth: {limit})...
                                        </div>
                                    </td>
                                </tr>
                            ) : markets.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="px-6 py-12 text-center text-slate-500 italic">
                                        No significant volatility detected in secondary markets.
                                    </td>
                                </tr>
                            ) : (
                                markets.map((market) => (
                                    <tr key={market.id || Math.random()} className="hover:bg-slate-800/30 transition-all duration-200">
                                        <td className="px-6 py-4 font-medium text-slate-200 max-w-md truncate">
                                            {(() => {
                                                const eventTitle = market.event?.title || (market.events?.[0]?.title);
                                                const eventSlug = market.event?.slug || (market.events?.[0]?.slug);

                                                return (
                                                    <div className="flex items-center gap-3">
                                                        <Layers className="w-3 h-3 text-slate-500" />
                                                        <div className="flex flex-col">
                                                            <span className="truncate text-slate-100 font-bold" title={eventTitle || market.question}>
                                                                {eventTitle || market.question || "Unknown Vector"}
                                                            </span>
                                                            {eventTitle && (
                                                                <span className="text-[10px] text-slate-400 font-medium truncate max-w-[280px]">
                                                                    {market.question}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            })()}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-emerald-400 font-semibold">
                                            {formatCurrency(market.volume || 0)}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-blue-400 font-medium">
                                            {formatCurrency(market.liquidity || 0)}
                                        </td>
                                        <td className="px-6 py-4">
                                            <a
                                                href={(() => {
                                                    const eSlug = market.event?.slug || (market.events?.[0]?.slug);
                                                    return eSlug
                                                        ? `https://polymarket.com/event/${eSlug}`
                                                        : `https://polymarket.com/market/${market.slug}`;
                                                })()}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center gap-1.5 mx-auto px-3 py-1.5 text-[10px] uppercase font-bold tracking-widest text-slate-400 hover:text-white bg-slate-800/40 hover:bg-slate-700/60 rounded-md transition-all border border-slate-700/50 w-fit"
                                            >
                                                <span>External</span>
                                                <ExternalLink className="w-2.5 h-2.5" />
                                            </a>
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
