export interface MarketStats {
    total_tracked: number;
    smart_money_count: number;
    total_volume: number;
    total_profit: number;
    cluster_alerts: number;
    by_grade: {
        WHALE: number;
        SHARK: number;
        ORCA: number;
        FISH: number;
        PLANKTON: number;
    };
}

export interface Wallet {
    address: string;
    grade: string;
    roi: number;
    win_rate: number;
    total_trades: number;
    profit_usdc: number;
    volume_usdc: number;
    is_smart_money: boolean;
    last_updated: string;
}

export interface ClusterAlert {
    alert_id: string;
    market_id: string;
    market_question: string;
    token_id: string;
    outcome: string;
    wallets: string[];
    wallet_grades: string[];
    wallet_count: number;
    avg_position_size: number;
    total_exposure: number;
    confidence: number;
    detected_at: string;
}

export interface MarketVector {
    id: string;
    question: string;
    volume: number;
    liquidity: number;
    slug: string;
    event?: {
        title: string;
        slug: string;
    };
    events?: {
        title: string;
        slug: string;
    }[];
}
