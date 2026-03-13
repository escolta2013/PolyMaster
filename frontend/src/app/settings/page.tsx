"use client";

import React from 'react';
import ProxyWalletCard from '@/components/ProxyWalletCard';
import { Shield, Cog, Lock, Zap, Bot } from 'lucide-react';

export default function SettingsPage() {
    // For now, we use a fixed user ID or we would pull this from Auth session
    const userId = "default-user-id";

    return (
        <div className="container mx-auto px-6 py-10 max-w-5xl">
            <header className="mb-10">
                <div className="flex items-center gap-2 mb-2">
                    <Cog className="w-5 h-5 text-slate-500" />
                    <span className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-500">System Management</span>
                </div>
                <h1 className="text-4xl font-black text-white tracking-tighter uppercase">
                    Account & Engine Settings
                </h1>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Sidebar Info */}
                <div className="lg:col-span-1 space-y-6">
                    <div className="bg-white/5 p-6 rounded-2xl border border-white/10">
                        <Lock className="text-blue-400 mb-4" size={24} />
                        <h4 className="text-white font-bold mb-2">Security Standard</h4>
                        <p className="text-gray-400 text-sm">
                            PolyMaster uses an institutional-grade proxy wallet system. Private keys are never stored on your device and are encrypted using AES-256.
                        </p>
                    </div>

                    <div className="bg-white/5 p-6 rounded-2xl border border-white/10">
                        <Zap className="text-yellow-400 mb-4" size={24} />
                        <h4 className="text-white font-bold mb-2">Execution Layer</h4>
                        <p className="text-gray-400 text-sm">
                            Orders are routed through your proxy wallet to ensure zero-latency execution and maximum anonymity on-chain.
                        </p>
                    </div>
                </div>

                {/* Right Column - Wallet Manager */}
                <div className="lg:col-span-2">
                    <ProxyWalletCard userId={userId} />

                    {/* Phase 5: Autonomous Director Control */}
                    <div className="mt-8 bg-black/40 backdrop-blur-md border border-purple-500/20 rounded-xl p-6 relative overflow-hidden group hover:border-purple-500/40 transition-all duration-300">
                        <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                        <div className="relative z-10">
                            <div className="flex justify-between items-center mb-6">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-purple-500/20 rounded-lg text-purple-400">
                                        <Bot size={24} />
                                    </div>
                                    <div>
                                        <h2 className="text-lg font-bold text-white flex items-center gap-2">
                                            Autonomous Director
                                            <span className="bg-purple-500/10 text-purple-400 text-[10px] px-2 py-0.5 rounded border border-purple-500/20">BETA</span>
                                        </h2>
                                        <p className="text-gray-400 text-xs">AI Brain that executes trades automatically</p>
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="flex items-center justify-between bg-black/20 p-4 rounded-lg border border-white/5">
                                    <div className="text-sm">
                                        <div className="text-gray-300 font-medium">Auto-Pilot Mode</div>
                                        <div className="text-gray-500 text-xs mt-1 max-w-sm">
                                            Allows the Director to execute trades without confirmation when Council Consensus is high.
                                        </div>
                                    </div>

                                    <label className="relative inline-flex items-center cursor-pointer">
                                        <input
                                            type="checkbox"
                                            className="sr-only peer"
                                            onChange={async (e) => {
                                                const checkbox = e.target;
                                                const newVal = checkbox.checked;
                                                try {
                                                    /* 
                                                     * Note: In a real app we'd fetch initial state and use SWR/store.
                                                     * For this MVP we just optimistically toggle.
                                                     */
                                                    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/director/toggle`, {
                                                        method: 'POST',
                                                        headers: {
                                                            'Content-Type': 'application/json',
                                                            'X-API-KEY': process.env.NEXT_PUBLIC_MASTER_API_KEY || ""
                                                        },
                                                        body: JSON.stringify({ enabled: newVal })
                                                    });
                                                    if (!res.ok) throw new Error("Toggle failed");
                                                    alert(`Autonomous Mode ${newVal ? 'ENABLED' : 'DISABLED'}`);
                                                } catch (err) {
                                                    alert("Failed to toggle director. Backend might be offline.");
                                                    checkbox.checked = !newVal; // Revert
                                                }
                                            }}
                                        />
                                        <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-purple-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                                    </label>
                                </div>
                                <div className="flex gap-4 text-xs text-gray-500 pt-2 border-t border-white/5">
                                    <div className="flex items-center gap-1">
                                        <Shield size={12} className="text-purple-400" />
                                        <span>Confidence: <span className="text-gray-300">85%</span></span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <text className="text-purple-400">$</text>
                                        <span>Max Size: <span className="text-gray-300">$50.00</span></span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="mt-8 p-6 bg-red-500/5 rounded-2xl border border-red-500/10">
                        <h4 className="text-red-400 font-bold mb-2 flex items-center gap-2">
                            <Shield size={18} />
                            Danger Zone
                        </h4>
                        <p className="text-gray-400 text-sm mb-4">
                            Regenerating your proxy wallet will lose access to the current address. Ensure you have withdrawn all funds before proceeding.
                        </p>
                        <button className="text-red-400 text-xs font-bold uppercase tracking-widest border border-red-500/20 px-4 py-2 rounded hover:bg-red-500/10 transition-colors">
                            Reset Engine Credentials
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
