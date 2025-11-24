"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  Bot,
  Clock,
  MessageSquare,
  Play,
  Power,
  RefreshCw,
  SquareTerminal,
  TrendingUp,
  Twitter,
  X,
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Custom X (Twitter) Icon Component
function XIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      viewBox="0 0 24 24"
      fill="currentColor"
    >
      <title>X</title>
      <path d="M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z"></path>
    </svg>
  );
}

export default function Dashboard() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [trends, setTrends] = useState<any[]>([]);
  const [showTrendsModal, setShowTrendsModal] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch("http://127.0.0.1:5000/api/status");
      const data = await res.json();
      setStatus(data);

      // Fetch trends
      const trendsRes = await fetch("http://127.0.0.1:5000/api/trends");
      const trendsData = await trendsRes.json();
      setTrends(trendsData.trends || []);
    } catch (error) {
      console.error("Failed to fetch status:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const handleControl = async (action: "start" | "stop") => {
    setRefreshing(true);
    try {
      await fetch("http://127.0.0.1:5000/api/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      await fetchStatus();
    } catch (error) {
      console.error("Control error:", error);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-8 font-sans">
      {/* Header */}
      <header className="flex items-center justify-between mb-12">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-blue-500/10 rounded-2xl border border-blue-500/20">
            <Bot className="w-8 h-8 text-blue-500" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">AI Persona</h1>
            <p className="text-muted-foreground">Otonom Twitter Asistanı</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-medium transition-colors",
              status?.running
                ? "bg-green-500/10 border-green-500/20 text-green-500"
                : "bg-red-500/10 border-red-500/20 text-red-500"
            )}
          >
            <div
              className={cn(
                "w-2 h-2 rounded-full",
                status?.running ? "bg-green-500 animate-pulse" : "bg-red-500"
              )}
            />
            {status?.running ? "SİSTEM AKTİF" : "SİSTEM DURDURULDU"}
          </div>
        </div>
      </header>

      {/* Ana İstatistikler */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Günlük Tweetler */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <span className="text-muted-foreground text-sm font-medium">Günlük Tweetler</span>
            <Twitter className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-3xl font-bold">
            {status?.stats?.daily_tweets || 0}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Hedef: 12/gün
          </div>
        </Card>

        {/* Toplam Aktivite */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <span className="text-muted-foreground text-sm font-medium">
              Toplam Aktivite
            </span>
            <Activity className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-3xl font-bold">
            {status?.stats?.total_tweets || 0}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Tüm zamanlar
          </div>
        </Card>

        {/* Sonraki Döngü */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <span className="text-muted-foreground text-sm font-medium">
              Sonraki Döngü
            </span>
            <Clock className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-3xl font-bold font-mono">
            {status?.running ? "24:00" : "--:--"}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Kalan süre (dakika)
          </div>
        </Card>

        {/* Durum/Kontrol */}
        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-linear-to-br from-blue-500/5 to-purple-500/5" />
          <div className="relative z-10 h-full flex flex-col justify-between">
            <div className="flex items-center justify-between mb-4">
              <span className="text-muted-foreground text-sm font-medium">
                Sistem Kontrolü
              </span>
              <Power className="w-4 h-4 text-muted-foreground" />
            </div>
            <div className="flex gap-2">
              {!status?.running ? (
                <button
                  onClick={() => handleControl("start")}
                  disabled={refreshing}
                  className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-green-600/50 text-white py-2 rounded-lg font-medium transition-all active:scale-95 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {refreshing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Başlatılıyor...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" /> Botu Başlat
                    </>
                  )}
                </button>
              ) : (
                <button
                  onClick={() => handleControl("stop")}
                  disabled={refreshing}
                  className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-red-600/50 text-white py-2 rounded-lg font-medium transition-all active:scale-95 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {refreshing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Durduruluyor...
                    </>
                  ) : (
                    <>
                      <Power className="w-4 h-4" /> Botu Durdur
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </Card>
      </div>

      {/* Manuel Müdahale ve Gündem */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Manuel Müdahale */}
        <div className="lg:col-span-2">
          <Card className="h-full">
            <div className="flex items-center gap-2 mb-6">
              <SquareTerminal className="w-5 h-5 text-purple-500" />
              <h2 className="text-lg font-semibold">Manuel Müdahale</h2>
            </div>
            <ManualTweet />
          </Card>
        </div>

        {/* Gündem (Trending Topics) */}
        <div className="lg:col-span-1">
          <Card className="h-full">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-orange-500" />
                <h2 className="text-lg font-semibold">Gündem</h2>
              </div>
              <button
                onClick={() => setShowTrendsModal(true)}
                className="text-xs text-blue-500 hover:text-blue-400 transition-colors"
              >
                Devamını Gör →
              </button>
            </div>
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {trends.slice(0, 5).map((trend, idx) => (
                <div
                  key={idx}
                  className="bg-secondary/30 border border-border/50 rounded-lg p-3 hover:bg-secondary/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-start gap-3">
                    <div className="shrink-0 w-6 h-6 rounded-full bg-orange-500/10 border border-orange-500/20 flex items-center justify-center">
                      <span className="text-xs font-bold text-orange-500">#{idx + 1}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-semibold text-foreground line-clamp-2">
                        {trend.name || trend}
                      </h3>
                      {trend.tweet_count && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {trend.tweet_count} tweet
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {trends.length === 0 && (
                <div className="text-center text-muted-foreground py-8 text-sm">
                  Gündem yükleniyor...
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Recent Activity & Console */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Tweet */}
        <div className="lg:col-span-2">
          <Card className="h-full">
            <div className="flex items-center gap-2 mb-6">
              <MessageSquare className="w-5 h-5 text-blue-500" />
              <h2 className="text-lg font-semibold">Son İletim</h2>
            </div>
            {status?.stats?.last_tweet ? (
              <div className="bg-secondary/50 p-6 rounded-xl border border-border/50">
                <p className="text-lg leading-relaxed text-foreground/90">
                  "{status.stats.last_tweet}"
                </p>
                <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="w-3 h-3" />
                  <span>{status.stats.last_tweet_time}</span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                <div className="w-12 h-12 rounded-full bg-secondary/50 flex items-center justify-center mb-3">
                  <MessageSquare className="w-6 h-6 opacity-50" />
                </div>
                <p>Henüz kayıtlı aktivite yok</p>
              </div>
            )}
          </Card>
        </div>

        {/* Mini Konsol */}
        <div className="lg:col-span-1">
          <Card className="h-full bg-black/40 border-border/50 font-mono text-sm">
            <div className="flex items-center gap-2 mb-4 text-muted-foreground border-b border-border/20 pb-2">
              <SquareTerminal className="w-4 h-4" />
              <span>Sistem Logları</span>
            </div>
            <div className="space-y-2 text-xs opacity-80">
              <div className="flex gap-2">
                <span className="text-green-500">[BİLGİ]</span>
                <span>Sistem başlatıldı</span>
              </div>
              <div className="flex gap-2">
                <span className="text-blue-500">[AĞ]</span>
                <span>Twitter API v2 bağlantısı kuruldu</span>
              </div>
              <div className="flex gap-2">
                <span className="text-purple-500">[AI]</span>
                <span>Gemini 1.5 Flash hazır</span>
              </div>
              <div className="flex gap-2">
                <span className="text-yellow-500">[BEKLE]</span>
                <span>Sonraki döngü bekleniyor...</span>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Trends Modal */}
      {showTrendsModal && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setShowTrendsModal(false)}
        >
          <div
            className="bg-card border border-border rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-3">
                <TrendingUp className="w-6 h-6 text-orange-500" />
                <h2 className="text-xl font-bold">Türkiye Gündemi</h2>
              </div>
              <button
                onClick={() => setShowTrendsModal(false)}
                className="p-2 hover:bg-secondary rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-100px)]">
              <div className="space-y-3">
                {trends.map((trend, idx) => (
                  <div
                    key={idx}
                    className="bg-secondary/30 border border-border/50 rounded-lg p-4 hover:bg-secondary/50 transition-all hover:border-blue-500/30"
                  >
                    <div className="flex items-start gap-3">
                      <div className="shrink-0 w-8 h-8 rounded-full bg-orange-500/10 border border-orange-500/20 flex items-center justify-center">
                        <span className="text-sm font-bold text-orange-500">#{idx + 1}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-foreground mb-1 wrap-break-word">
                          {trend.name || trend}
                        </h3>
                        {trend.tweet_count && (
                          <p className="text-xs text-muted-foreground">
                            {trend.tweet_count} tweet
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ManualTweet() {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);

  const handleSend = async () => {
    if (!text.trim()) return;
    setSending(true);
    try {
      const res = await fetch("http://127.0.0.1:5000/api/tweet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, persona: "casual" }),
      });
      const data = await res.json();
      if (data.success) {
        setText("");
        alert("Tweet başarıyla gönderildi!");
      } else {
        alert("Tweet gönderilemedi: " + data.message);
      }
    } catch (error) {
      console.error("Tweet error:", error);
      alert("Tweet gönderme hatası");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-4">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Manuel tweet içeriğini buraya yazın..."
        className="w-full h-32 bg-secondary/30 border border-border rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
      />
      <div className="flex justify-end">
        <button
          onClick={handleSend}
          disabled={sending || !text.trim()}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {sending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <XIcon className="w-4 h-4" />}
          Gönderi Yayınla
        </button>
      </div>
    </div>
  );
}

function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "bg-card border border-border rounded-xl p-6 shadow-sm",
        className
      )}
    >
      {children}
    </div>
  );
}
