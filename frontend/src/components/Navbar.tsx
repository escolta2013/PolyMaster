"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, Ghost, Bot, Zap, Wallet } from "lucide-react"

export function Navbar() {
    const pathname = usePathname();

    const getLinkClass = (path: string) => {
        const isActive = pathname === path;
        return `flex items-center space-x-2 text-sm font-medium transition-colors ${isActive ? "text-white" : "text-muted-foreground hover:text-white"
            }`;
    };

    return (
        <nav className="border-b border-white/10 bg-black/50 backdrop-blur-md sticky top-0 z-50">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                <Link href="/" className="flex items-center space-x-2 hover:opacity-80 transition-opacity">
                    <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
                        <Zap className="w-5 h-5 text-white" />
                    </div>
                    <span className="font-bold text-xl tracking-tight text-white">PolyMaster</span>
                </Link>

                <div className="hidden md:flex items-center space-x-6">
                    <Link href="/" className={getLinkClass("/")}>
                        <LayoutDashboard className="w-4 h-4" />
                        <span>Tracker</span>
                    </Link>
                    <Link href="/ghost" className={getLinkClass("/ghost")}>
                        <Ghost className="w-4 h-4" />
                        <span>Ghost</span>
                    </Link>
                    <Link href="/council" className={getLinkClass("/council")}>
                        <Bot className="w-4 h-4" />
                        <span>Council</span>
                    </Link>
                </div>

                <div className="flex items-center space-x-4">
                    <button className="flex items-center space-x-2 bg-emerald-500/20 text-emerald-400 px-4 py-2 rounded-full text-sm font-medium hover:bg-emerald-500/30 transition-colors border border-emerald-500/50">
                        <Wallet className="w-4 h-4" />
                        <span>Connect</span>
                    </button>
                </div>
            </div>
        </nav>
    )
}
