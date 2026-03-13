"use client"

import * as React from "react"
import { Bell, AlertTriangle, X, Users } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

interface Notification {
    id: string
    type: "cluster" | "info"
    title: string
    body: string
    time: string
    read: boolean
}

export function NotificationBell() {
    const [notifications, setNotifications] = React.useState<Notification[]>([])
    const [isOpen, setIsOpen] = React.useState(false)
    const [prevCount, setPrevCount] = React.useState(0)
    const panelRef = React.useRef<HTMLDivElement>(null)

    // Poll for cluster alerts and convert them to notifications
    React.useEffect(() => {
        const fetchAlerts = async () => {
            try {
                const res = await fetch(`${API_URL}/tracker/clusters/alerts?limit=5`)
                if (!res.ok) return
                const alerts = await res.json()

                const notifs: Notification[] = (alerts || []).map((a: any) => ({
                    id: a.alert_id,
                    type: "cluster" as const,
                    title: `Cluster: ${a.wallet_count} whales on ${a.outcome}`,
                    body: a.market_question || "Unknown market",
                    time: a.detected_at,
                    read: false,
                }))
                setNotifications(notifs)

                // Trigger visual pulse when new alerts arrive
                if (notifs.length > prevCount) {
                    setPrevCount(notifs.length)
                }
            } catch {
                // silent fail
            }
        }
        fetchAlerts()
        const interval = setInterval(fetchAlerts, 20000)
        return () => clearInterval(interval)
    }, [prevCount])

    // Close panel on outside click
    React.useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
                setIsOpen(false)
            }
        }
        if (isOpen) document.addEventListener("mousedown", handler)
        return () => document.removeEventListener("mousedown", handler)
    }, [isOpen])

    const unreadCount = notifications.filter(n => !n.read).length

    const timeAgo = (dateStr: string) => {
        const diff = Date.now() - new Date(dateStr).getTime()
        const mins = Math.floor(diff / 60000)
        if (mins < 1) return "now"
        if (mins < 60) return `${mins}m`
        const hrs = Math.floor(mins / 60)
        if (hrs < 24) return `${hrs}h`
        return `${Math.floor(hrs / 24)}d`
    }

    return (
        <div className="relative" ref={panelRef}>
            {/* Bell button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="relative p-2 rounded-lg hover:bg-slate-800/50 transition-colors group"
            >
                <Bell className={`w-4 h-4 transition-colors ${unreadCount > 0 ? 'text-orange-400' : 'text-slate-500 group-hover:text-slate-300'
                    }`} />
                {unreadCount > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-orange-500 rounded-full flex items-center justify-center text-[8px] font-black text-white shadow-[0_0_8px_rgba(249,115,22,0.5)] animate-pulse">
                        {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                )}
            </button>

            {/* Dropdown panel */}
            {isOpen && (
                <div className="absolute right-0 top-full mt-2 w-80 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden z-50">
                    {/* Header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/50">
                        <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                            Notifications
                        </span>
                        {unreadCount > 0 && (
                            <button
                                onClick={() => setNotifications(ns => ns.map(n => ({ ...n, read: true })))}
                                className="text-[9px] text-blue-400 hover:text-blue-300 font-bold uppercase tracking-wider transition-colors"
                            >
                                Mark all read
                            </button>
                        )}
                    </div>

                    {/* List */}
                    <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/30">
                        {notifications.length === 0 ? (
                            <div className="px-4 py-8 text-center">
                                <Bell className="w-6 h-6 text-slate-700 mx-auto mb-2" />
                                <p className="text-[10px] text-slate-600 uppercase tracking-widest">No alerts yet</p>
                            </div>
                        ) : (
                            notifications.map((n) => (
                                <div
                                    key={n.id}
                                    className={`px-4 py-3 hover:bg-slate-800/30 transition-colors cursor-default ${!n.read ? 'bg-orange-500/[0.02]' : ''
                                        }`}
                                >
                                    <div className="flex items-start gap-3">
                                        <div className="mt-0.5">
                                            {n.type === "cluster" ? (
                                                <Users className="w-3.5 h-3.5 text-orange-500" />
                                            ) : (
                                                <AlertTriangle className="w-3.5 h-3.5 text-blue-500" />
                                            )}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-[11px] font-bold text-slate-200 leading-snug">{n.title}</p>
                                            <p className="text-[10px] text-slate-500 mt-0.5 truncate">{n.body}</p>
                                        </div>
                                        <span className="text-[9px] text-slate-600 font-mono whitespace-nowrap">
                                            {timeAgo(n.time)}
                                        </span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
