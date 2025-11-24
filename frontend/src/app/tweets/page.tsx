"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Check,
  Clock,
  Filter,
  RefreshCw,
  Trash2,
  X as XClose
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

interface Tweet {
  id: number;
  text: string;
  type: string;
  sent: boolean;
  created_at: string;
  persona?: string;
}

export default function TweetsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [tweets, setTweets] = useState<Tweet[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState(searchParams.get("filter") || "all");
  const [page, setPage] = useState(parseInt(searchParams.get("page") || "1"));
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    fetchTweets();
  }, [filter, page]);

  const fetchTweets = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `http://127.0.0.1:5000/api/tweets?filter=${filter}&page=${page}&per_page=20`
      );
      const data = await res.json();
      setTweets(data.tweets || []);
      setTotalCount(data.total || 0);
    } catch (error) {
      console.error("Failed to fetch tweets:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (newFilter: string) => {
    setFilter(newFilter);
    setPage(1);
    router.push(`/tweets?filter=${newFilter}&page=1`);
  };

  const handleRetry = async (tweetId: number) => {
    if (!confirm("Bu tweet'i tekrar göndermek istediğinizden emin misiniz?")) return;

    try {
      const res = await fetch(`http://127.0.0.1:5000/api/retry_tweet/${tweetId}`, {
        method: "POST",
      });
      const data = await res.json();
      if (data.success) {
        alert("Tweet başarıyla tekrar gönderildi!");
        fetchTweets();
      } else {
        alert("Hata: " + data.message);
      }
    } catch (error) {
      console.error("Retry error:", error);
    }
  };

  const handleDelete = async (tweetId: number) => {
    if (!confirm("Bu tweet'i silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.")) return;

    try {
      const res = await fetch(`http://127.0.0.1:5000/api/delete_tweet/${tweetId}`, {
        method: "DELETE",
      });
      const data = await res.json();
      if (data.success) {
        alert("Tweet başarıyla silindi!");
        fetchTweets();
      } else {
        alert("Hata: " + data.message);
      }
    } catch (error) {
      console.error("Delete error:", error);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/")}
            className="p-2 hover:bg-secondary rounded-lg transition-colors"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Tweet Geçmişi</h1>
            <p className="text-muted-foreground">{totalCount} kayıt</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-6">
        <FilterButton
          active={filter === "all"}
          onClick={() => handleFilterChange("all")}
          icon={<Filter className="w-4 h-4" />}
          label="Tümü"
        />
        <FilterButton
          active={filter === "success"}
          onClick={() => handleFilterChange("success")}
          icon={<Check className="w-4 h-4" />}
          label="Başarılı"
          color="green"
        />
        <FilterButton
          active={filter === "failed"}
          onClick={() => handleFilterChange("failed")}
          icon={<XClose className="w-4 h-4" />}
          label="Başarısız"
          color="red"
        />
        <FilterButton
          active={filter === "manual"}
          onClick={() => handleFilterChange("manual")}
          icon={<XIcon className="w-4 h-4" />}
          label="Manuel"
          color="blue"
        />
      </div>

      {/* Tweets List */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : tweets.length > 0 ? (
        <div className="space-y-3">
          {tweets.map((tweet) => (
            <TweetCard
              key={tweet.id}
              tweet={tweet}
              onRetry={handleRetry}
              onDelete={handleDelete}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
          <XIcon className="w-16 h-16 mb-4 opacity-20" />
          <p className="text-lg">Henüz tweet bulunamadı</p>
          <p className="text-sm">Bot çalışmaya başladığında tweetler burada görünecek</p>
        </div>
      )}

      {/* Pagination */}
      {totalCount > 20 && (
        <div className="flex justify-center gap-2 mt-8">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Önceki
          </button>
          <span className="px-4 py-2 bg-secondary rounded-lg">
            Sayfa {page}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={tweets.length < 20}
            className="px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Sonraki
          </button>
        </div>
      )}
    </div>
  );
}

function FilterButton({
  active,
  onClick,
  icon,
  label,
  color = "gray"
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  color?: string;
}) {
  const colorClasses = {
    gray: "border-border hover:bg-secondary",
    green: "border-green-500/20 hover:bg-green-500/10 text-green-500",
    red: "border-red-500/20 hover:bg-red-500/10 text-red-500",
    blue: "border-blue-500/20 hover:bg-blue-500/10 text-blue-500",
  };

  return (
    <button
      onClick={onClick}
      className={cn(
        "px-4 py-2 rounded-lg border transition-colors flex items-center gap-2 cursor-pointer",
        active ? "bg-secondary border-blue-500" : colorClasses[color as keyof typeof colorClasses]
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function TweetCard({
  tweet,
  onRetry,
  onDelete
}: {
  tweet: Tweet;
  onRetry: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const isLong = tweet.text.length > 150;
  const displayText = expanded || !isLong ? tweet.text : tweet.text.substring(0, 150) + "...";

  return (
    <div className="bg-card border border-border rounded-xl p-4 hover:border-blue-500/30 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-foreground leading-relaxed whitespace-pre-wrap wrap-break-word">
            {displayText}
          </p>
          {isLong && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-blue-500 text-sm mt-2 hover:underline"
            >
              {expanded ? "Kısalt" : "Devamını göster"}
            </button>
          )}
          <div className="flex items-center gap-3 mt-3 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {tweet.created_at}
            </div>
            {tweet.type === "manual" ? (
              <span className="px-2 py-0.5 bg-blue-500/10 border border-blue-500/20 text-blue-500 rounded text-xs">
                Manuel
              </span>
            ) : (
              <span className="px-2 py-0.5 bg-purple-500/10 border border-purple-500/20 text-purple-500 rounded text-xs">
                Otomatik
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {tweet.sent ? (
            <span className="px-3 py-1 bg-green-500/10 border border-green-500/20 text-green-500 rounded-lg text-sm flex items-center gap-1">
              <Check className="w-4 h-4" />
              Başarılı
            </span>
          ) : (
            <>
              <span className="px-3 py-1 bg-red-500/10 border border-red-500/20 text-red-500 rounded-lg text-sm flex items-center gap-1">
                <XClose className="w-4 h-4" />
                Başarısız
              </span>
              <button
                onClick={() => onRetry(tweet.id)}
                className="p-2 hover:bg-blue-500/10 border border-blue-500/20 text-blue-500 rounded-lg transition-colors cursor-pointer"
                title="Tekrar gönder"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </>
          )}
          <button
            onClick={() => onDelete(tweet.id)}
            className="p-2 hover:bg-red-500/10 border border-red-500/20 text-red-500 rounded-lg transition-colors cursor-pointer"
            title="Sil"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
