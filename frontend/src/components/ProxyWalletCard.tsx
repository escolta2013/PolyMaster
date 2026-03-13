"use client";

import React, { useState, useEffect } from 'react';
import { Wallet, ShieldCheck, RefreshCw, Key, ArrowUpRight, Copy, CheckCircle2 } from 'lucide-react';
import { getWalletStatus, generateWallet, refreshWalletBalance } from '@/lib/api';

interface ProxyWalletProps {
    userId: string;
}

const ProxyWalletCard: React.FC<ProxyWalletProps> = ({ userId }) => {
    const [status, setStatus] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(false);
    const [showCopied, setShowCopied] = useState(false);

    const loadStatus = async () => {
        try {
            const data = await getWalletStatus(userId);
            setStatus(data);
        } catch (error) {
            console.error("Error loading wallet status:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadStatus();
    }, [userId]);

    const handleGenerate = async () => {
        setActionLoading(true);
        try {
            await generateWallet(userId);
            await loadStatus();
        } catch (error) {
            alert("Failed to generate wallet. Please try again.");
        } finally {
            setActionLoading(false);
        }
    };

    const handleRefresh = async () => {
        setActionLoading(true);
        try {
            await refreshWalletBalance(userId);
            await loadStatus();
        } catch (error) {
            console.error(error);
        } finally {
            setActionLoading(false);
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        setShowCopied(true);
        setTimeout(() => setShowCopied(false), 2000);
    };

    if (loading) {
        return <div className="animate-pulse bg-white/5 h-64 rounded-xl border border-white/10" />;
    }

    if (!status?.has_wallet) {
        return (
            <div className="bg-gradient-to-br from-[#0f172a] to-[#1e293b] p-8 rounded-2xl border border-blue-500/20 shadow-2xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                    <Wallet size={120} />
                </div>

                <h3 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                    <ShieldCheck className="text-blue-400" />
                    Secure Proxy Wallet
                </h3>
                <p className="text-gray-400 mb-6 max-w-md">
                    To execute trades on Polymarket, we create a secure, isolated "proxy" wallet for your account.
                    You maintain control, and your main keys are never exposed.
                </p>

                <button
                    onClick={handleGenerate}
                    disabled={actionLoading}
                    className="bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 px-8 rounded-lg transition-all transform hover:scale-105 active:scale-95 disabled:opacity-50 flex items-center gap-2"
                >
                    {actionLoading ? <RefreshCw className="animate-spin" size={20} /> : <Key size={20} />}
                    Generate My Proxy Wallet
                </button>
            </div>
        );
    }

    return (
        <div className="bg-gradient-to-br from-[#0f172a] to-[#1e293b] p-6 rounded-2xl border border-green-500/20 shadow-2xl">
            <div className="flex justify-between items-start mb-6">
                <div>
                    <span className="text-xs font-bold text-green-400 uppercase tracking-widest bg-green-400/10 px-2 py-1 rounded mb-2 inline-block">
                        Active Proxy
                    </span>
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        Institutional Wallet
                    </h3>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={actionLoading}
                    className="p-2 bg-white/5 hover:bg-white/10 rounded-full transition-colors text-gray-400 hover:text-white"
                >
                    <RefreshCw className={actionLoading ? "animate-spin" : ""} size={20} />
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                    <div className="text-gray-500 text-sm mb-1 uppercase font-semibold">Balance (USDC)</div>
                    <div className="text-3xl font-mono text-white flex items-baseline gap-2">
                        ${status.balance.toFixed(2)}
                        <span className="text-sm text-gray-400 font-sans">USDC</span>
                    </div>
                </div>

                <div className="bg-black/20 p-4 rounded-xl border border-white/5 flex flex-col justify-center">
                    <div className="text-gray-500 text-sm mb-1 uppercase font-semibold">Account Health</div>
                    <div className="flex items-center gap-2 text-green-400 font-bold">
                        <ShieldCheck size={18} />
                        Fully Encrypted
                    </div>
                </div>
            </div>

            <div className="space-y-4">
                <div className="relative">
                    <div className="text-gray-500 text-sm mb-1 px-1">Deposit Address (Polygon)</div>
                    <div className="flex items-center gap-2 bg-black/40 p-3 rounded-lg border border-white/10 group">
                        <div className="text-xs font-mono text-gray-300 truncate flex-1">
                            {status.address}
                        </div>
                        <button
                            onClick={() => copyToClipboard(status.address)}
                            className="text-gray-500 hover:text-white transition-colors relative"
                        >
                            {showCopied ? <CheckCircle2 size={16} className="text-green-400" /> : <Copy size={16} />}
                        </button>
                    </div>
                </div>

                <div className="flex gap-2">
                    <a
                        href={`https://polygonscan.com/address/${status.address}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 bg-white/5 hover:bg-white/10 text-white py-2 rounded-lg text-sm text-center flex items-center justify-center gap-2 transition-colors border border-white/10"
                    >
                        View on Explorer
                        <ArrowUpRight size={14} />
                    </a>
                </div>

                {/* Withdrawal Section */}
                <div className="mt-6 pt-6 border-t border-white/5">
                    <h4 className="text-white font-bold mb-4 text-sm flex items-center gap-2">
                        <ArrowUpRight size={16} className="text-orange-400" />
                        Quick Withdrawal
                    </h4>
                    <div className="space-y-3">
                        <input
                            id="withdraw-address"
                            type="text"
                            placeholder="Target Polygon Address (0x...)"
                            className="w-full bg-black/40 border border-white/10 rounded-lg p-3 text-xs text-white placeholder:text-gray-600 focus:outline-none focus:border-blue-500/50"
                        />
                        <div className="flex gap-2">
                            <input
                                id="withdraw-amount"
                                type="number"
                                placeholder="Amount USDC"
                                className="flex-1 bg-black/40 border border-white/10 rounded-lg p-3 text-xs text-white placeholder:text-gray-600 focus:outline-none focus:border-blue-500/50"
                            />
                            <button
                                onClick={async () => {
                                    const addr = (document.getElementById('withdraw-address') as HTMLInputElement).value;
                                    const amt = (document.getElementById('withdraw-amount') as HTMLInputElement).value;
                                    if (!addr || !amt) return alert("Address and amount required");
                                    setActionLoading(true);
                                    try {
                                        const { withdrawFunds } = await import('@/lib/api');
                                        const res = await withdrawFunds(userId, addr, parseFloat(amt));
                                        alert(`Success! TX: ${res.tx_hash}`);
                                        loadStatus();
                                    } catch (e: any) {
                                        alert(e.message);
                                    } finally {
                                        setActionLoading(false);
                                    }
                                }}
                                disabled={actionLoading}
                                className="bg-orange-600/20 hover:bg-orange-600/30 text-orange-400 px-4 py-2 rounded-lg text-xs font-bold transition-colors border border-orange-500/20"
                            >
                                Withdraw
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProxyWalletCard;
