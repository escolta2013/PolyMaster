import { MarketStats, Wallet, ClusterAlert, MarketVector } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function getStats(): Promise<MarketStats> {
    const res = await fetch(`${BASE_URL}/tracker/stats`, { next: { revalidate: 60 } });
    if (!res.ok) throw new Error("Failed to fetch stats");
    return res.json();
}

export async function getWallets(limit: number = 20): Promise<Wallet[]> {
    const res = await fetch(`${BASE_URL}/tracker/wallets?limit=${limit}`, { next: { revalidate: 30 } });
    if (!res.ok) throw new Error("Failed to fetch wallets");
    const data = await res.json();
    return data.wallets || [];
}

export async function getTopMarkets(limit: number = 10): Promise<MarketVector[]> {
    const res = await fetch(`${BASE_URL}/tracker/top-markets?limit=${limit}`, { next: { revalidate: 120 } });
    if (!res.ok) throw new Error("Failed to fetch markets");
    const data = await res.json();
    return data.markets || [];
}

export async function getClusterAlerts(limit: number = 10): Promise<ClusterAlert[]> {
    const res = await fetch(`${BASE_URL}/tracker/clusters/alerts?limit=${limit}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch alerts");
    return res.json();
}

// --- Wallet Manager API ---

const getHeaders = () => ({
    'Content-Type': 'application/json',
    'X-API-KEY': process.env.NEXT_PUBLIC_MASTER_API_KEY || ""
});

export async function getWalletStatus(userId: string) {
    const res = await fetch(`${BASE_URL}/wallet/status/${userId}`, {
        cache: 'no-store',
        headers: getHeaders()
    });
    if (!res.ok) throw new Error("Failed to fetch wallet status");
    return res.json();
}

export async function generateWallet(userId: string) {
    const res = await fetch(`${BASE_URL}/wallet/generate/${userId}`, {
        method: 'POST',
        headers: getHeaders()
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to generate wallet");
    }
    return res.json();
}

export async function refreshWalletBalance(userId: string) {
    const res = await fetch(`${BASE_URL}/wallet/balance/${userId}`, {
        cache: 'no-store',
        headers: getHeaders()
    });
    if (!res.ok) throw new Error("Failed to refresh balance");
    return res.json();
}

export async function withdrawFunds(userId: string, address: string, amount: number) {
    const res = await fetch(`${BASE_URL}/wallet/withdraw/${userId}`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ address, amount })
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Withdrawal failed");
    }
    return res.json();
}
