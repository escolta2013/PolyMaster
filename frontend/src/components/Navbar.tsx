import Link from "next/link"
import { LayoutDashboard, Ghost, Bot, Zap, Wallet } from "lucide-react"

export function Navbar() {
    return (
        <nav className="border-b border-white/10 bg-black/50 backdrop-blur-md sticky top-0 z-50">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                        <Zap className="w-5 h-5 text-white" />
                    </div>
                    <span className="font-bold text-xl tracking-tight">PolyMaster</span>
                </div>

                <div className="hidden md:flex items-center space-x-6">
                    <Link href="/" className="flex items-center space-x-2 text-sm font-medium text-white hover:text-primary transition-colors">
                        <LayoutDashboard className="w-4 h-4" />
                        <span>Tracker</span>
                    </Link>
                    <Link href="/ghost" className="flex items-center space-x-2 text-sm font-medium text-muted-foreground hover:text-white transition-colors">
                        <Ghost className="w-4 h-4" />
                        <span>Ghost</span>
                    </Link>
                    <Link href="/council" className="flex items-center space-x-2 text-sm font-medium text-muted-foreground hover:text-white transition-colors">
                        <Bot className="w-4 h-4" />
                        <span>Council</span>
                    </Link>
                </div>

                <div className="flex items-center space-x-4">
                    <button className="flex items-center space-x-2 bg-primary/20 text-primary px-4 py-2 rounded-full text-sm font-medium hover:bg-primary/30 transition-colors border border-primary/50">
                        <Wallet className="w-4 h-4" />
                        <span>Connect</span>
                    </button>
                </div>
            </div>
        </nav>
    )
}
