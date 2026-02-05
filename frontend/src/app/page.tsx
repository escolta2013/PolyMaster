import { SmartMoneyTable } from "@/components/SmartMoneyTable";
import { SmartMoneyWallets } from "@/components/SmartMoneyWallets";
import { TrendingUp, Users, Wallet, Target } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      {/* Hero Section */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-white to-white/40 bg-clip-text text-transparent italic">
            POLYMASTER <span className="text-primary not-italic">CORE</span>
          </h1>
          <p className="text-muted-foreground mt-1 flex items-center">
            <Target className="w-4 h-4 mr-2 text-primary" />
            Institutional Quantitative Intelligence Engine
          </p>
        </div>
        <div className="flex space-x-2">
          <div className="px-4 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-xs font-bold text-emerald-400 flex items-center shadow-[0_0_15px_rgba(16,185,129,0.1)]">
            <div className="w-2 h-2 bg-emerald-500 rounded-full mr-2 animate-pulse" />
            NODE: LONDRES-01 ACTIVE
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-white/[0.02] border-white/5 backdrop-blur-xl">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Neural Detectors</CardTitle>
            <Users className="h-4 w-4 text-primary opacity-50" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black">127 <span className="text-xs font-normal text-muted-foreground">Wallets</span></div>
            <p className="text-[10px] text-muted-foreground uppercase mt-1 tracking-tighter">Scanning 24/7 whale movement</p>
          </CardContent>
        </Card>
        <Card className="bg-white/[0.02] border-white/5 backdrop-blur-xl">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Alpha Yield</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-500 opacity-50" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-emerald-500">+$24,580</div>
            <p className="text-[10px] text-muted-foreground uppercase mt-1 tracking-tighter">Weighted Performance Score</p>
          </CardContent>
        </Card>
        <Card className="bg-white/[0.02] border-white/5 backdrop-blur-xl">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Liquidity Scan</CardTitle>
            <Wallet className="h-4 w-4 text-blue-500 opacity-50" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black">$1.2M</div>
            <p className="text-[10px] text-muted-foreground uppercase mt-1 tracking-tighter">Total Delta Exposure</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 gap-8">
        <div className="space-y-8">
          <SmartMoneyTable />
          <SmartMoneyWallets />
        </div>
      </div>
    </div>
  );
}
