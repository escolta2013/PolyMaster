"use client"

import * as React from "react"

export function SystemTime() {
    const [time, setTime] = React.useState("")

    React.useEffect(() => {
        setTime(new Date().toLocaleTimeString())
        const t = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000)
        return () => clearInterval(t)
    }, [])

    return (
        <div className="text-[10px] text-slate-500 font-mono uppercase tracking-tighter">
            Last Block Sync: {time || "--:--:--"}
        </div>
    )
}

export function LiveSystemStatus() {
    return (
        <div className="flex flex-col items-end gap-2">
            <div className="px-4 py-1.5 bg-emerald-500/5 border border-emerald-500/20 rounded-sm text-[10px] font-black text-emerald-400 flex items-center tracking-widest uppercase">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-3 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse" />
                Quantum-Node: Active
            </div>
            <SystemTime />
        </div>
    )
}
