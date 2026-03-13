"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, Ghost, Bot, Zap, Wallet, Shield } from "lucide-react"
import { NotificationBell } from "@/components/NotificationBell"

export function Navbar() {
    const pathname = usePathname();

    const getLinkClass = (path: string) => {
        const isActive = pathname === path;
        return `flex items-center gap-2 text-[10px] uppercase font-black tracking-[0.2em] transition-all duration-300 py-1.5 px-3 rounded ${isActive
            ? "text-emerald-400 bg-emerald-500/10 shadow-[0_0_15px_rgba(16,185,129,0.1)] border border-emerald-500/20"
            : "text-slate-500 hover:text-slate-200 border border-transparent"
            }`;
    };

    return (
        <nav className="border-b border-white/5 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-50">
            <div className="container mx-auto px-6 h-20 flex items-center justify-between max-w-7xl">
                <Link href="/" className="flex items-center gap-4 hover:opacity-80 transition-opacity group">
                    <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center shadow-2xl transform group-hover:scale-105 transition-transform">
                        <Shield className="w-6 h-6 text-slate-950" />
                    </div>
                    <div className="flex flex-col">
                        <span className="font-black text-xl tracking-tighter text-slate-100 uppercase leading-none">PolyMaster</span>
                        <span className="text-[8px] font-black text-emerald-500 tracking-[0.4em] mt-1 uppercase">Node Intelligence</span>
                    </div>
                </Link>

                <div className="hidden md:flex items-center gap-4">
                    <Link href="/" className={getLinkClass("/")}>
                        <LayoutDashboard className="w-3.5 h-3.5" />
                        <span>Tracker</span>
                    </Link>
                    <Link href="/ghost" className={getLinkClass("/ghost")}>
                        <Ghost className="w-3.5 h-3.5" />
                        <span>Ghost Engine</span>
                    </Link>
                    <Link href="/council" className={getLinkClass("/council")}>
                        <Bot className="w-3.5 h-3.5" />
                        <span>The Council</span>
                    </Link>
                    <Link href="/settings" className={getLinkClass("/settings")}>
                        <Shield className="w-3.5 h-3.5" />
                        <span>Settings</span>
                    </Link>
                </div>

                <div className="flex items-center gap-6">
                    <NotificationBell />
                    <div className="h-4 w-px bg-white/10 hidden sm:block" />
                    <button className="flex items-center gap-3 bg-white hover:bg-slate-200 text-slate-950 px-6 py-2.5 rounded-lg text-xs font-black uppercase tracking-widest transition-all transform active:scale-95 shadow-xl">
                        <Wallet className="w-4 h-4" />
                        <span>Auth Wallet</span>
                    </button>
                </div>
            </div>
        </nav>
    )
}
