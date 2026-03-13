"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Activity, ExternalLink, Layers } from "lucide-react"
import { MarketVector } from "@/types"

function formatCurrency(num: number) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        notation: 'compact',
        maximumFractionDigits: 1
    }).format(num);
}

interface SmartMoneyTableProps {
    initialMarkets: MarketVector[];
}

export function SmartMoneyTable({ initialMarkets }: SmartMoneyTableProps) {
    const [markets, setMarkets] = React.useState<MarketVector[]>(initialMarkets)
    const [loading, setLoading] = React.useState(false)
    const [limit, setLimit] = React.useState(10)

    React.useEffect(() => {
        if (limit === 10 && markets === initialMarkets) return; // Skip first effect if same as initial

        async function fetchData() {
            setLoading(true)
            try {
                const url = `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/tracker/top-markets?limit=${limit}`;
                const res = await fetch(url)
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
        <Card className="w-full bg-slate-950/40 border-slate-800 backdrop-blur-md shadow-2xl">
            <CardHeader className="pb-4 border-b border-white/5">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-bold tracking-tighter flex items-center gap-2 text-slate-100 uppercase">
                        <Activity className="w-4 h-4 text-emerald-500" />
                        <span>High-Velocity Market Clusters</span>
                    </CardTitle>
                    <div className="flex items-center gap-3">
                        <select
                            value={limit}
                            onChange={(e) => setLimit(Number(e.target.value))}
                            className="bg-slate-900 border border-white/10 text-slate-300 text-[10px] uppercase font-bold px-2 py-1 rounded outline-none focus:border-emerald-500/50 cursor-pointer"
                        >
                            <option value={10}>Top 10</option>
                            <option value={25}>Top 25</option>
                            <option value={50}>Top 50</option>
                        </select>
                        <div className="px-3 py-1 bg-emerald-500/10 rounded-full text-[9px] font-black text-emerald-400 uppercase tracking-widest border border-emerald-500/20">
                            {markets.length} VECTORS ACTIVE
                        </div>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="pt-6">
                <div className="rounded border border-white/5 overflow-hidden bg-slate-950/20">
                    <table className="w-full text-xs text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-900/50 text-slate-500 border-b border-white/5 uppercase tracking-widest font-black">
                                <th className="px-6 py-4">Market Vector</th>
                                <th className="px-6 py-4 text-right">Volume (USDC)</th>
                                <th className="px-6 py-4 text-right">Liquidity Delta</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {loading ? (
                                <tr>
                                    <td colSpan={3} className="px-6 py-12 text-center text-slate-400 font-medium">
                                        <div className="flex items-center justify-center gap-3">
                                            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                                            Re-scanning Vector Field...
                                        </div>
                                    </td>
                                </tr>
                            ) : markets.length === 0 ? (
                                <tr>
                                    <td colSpan={3} className="px-6 py-12 text-center text-slate-500 italic">
                                        No significant volatility detected.
                                    </td>
                                </tr>
                            ) : (
                                markets.map((market) => (
                                    <tr key={market.id} className="hover:bg-white/5 transition-all duration-200 group">
                                        <td className="px-6 py-4 font-medium text-slate-200 max-w-md truncate">
                                            {(() => {
                                                const eventTitle = market.event?.title || (market.events?.[0]?.title);
                                                const eSlug = market.event?.slug || (market.events?.[0]?.slug);
                                                const externalUrl = eSlug
                                                    ? `https://polymarket.com/event/${eSlug}`
                                                    : `https://polymarket.com/market/${market.id}`;

                                                return (
                                                    <a
                                                        href={externalUrl}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="flex items-center gap-3 hover:text-emerald-400 transition-colors"
                                                    >
                                                        <Layers className="w-3.5 h-3.5 text-slate-600 group-hover:text-emerald-500 transition-colors" />
                                                        <div className="flex flex-col">
                                                            <div className="flex items-center gap-2">
                                                                <span className="truncate text-slate-100 font-bold group-hover:text-emerald-400" title={eventTitle || market.question}>
                                                                    {eventTitle || market.question || "Unknown Vector"}
                                                                </span>
                                                                <ExternalLink className="w-2.5 h-2.5 opacity-0 group-hover:opacity-40 transition-opacity" />
                                                            </div>
                                                            {eventTitle && (
                                                                <span className="text-[10px] text-slate-500 font-medium truncate max-w-[300px]">
                                                                    {market.question}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </a>
                                                );
                                            })()}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-emerald-400 font-bold">
                                            {formatCurrency(market.volume || 0)}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-blue-400/80 font-medium">
                                            {formatCurrency(market.liquidity || 0)}
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
