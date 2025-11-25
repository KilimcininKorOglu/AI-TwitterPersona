"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Save,
  Settings,
  Moon,
  Sun,
  Clock,
  Globe,
  Shield,
  Zap
} from "lucide-react";
import { apiFetch } from "../../lib/api";

export default function SettingsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState({
    cycle_duration: 3600,
    sleep_start: 23,
    sleep_end: 7,
    timezone_offset: 3,
    trends_limit: 20,
    ai_model: "gemini-2.5-flash",
    temperature: 0.85,
    max_tokens: 1000
  });

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await apiFetch("/api/config");
      const data = await res.json();
      if (data.success) {
        setConfig(data.config);
      }
    } catch (error: any) {
      if (error?.status === 401) {
        router.push("/login");
        return;
      }
      console.error("Config fetch error:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await apiFetch("/api/config", {
        method: "POST",
        body: JSON.stringify(config),
      });
      const data = await res.json();
      if (data.success) {
        alert("Ayarlar başarıyla kaydedildi!");
      } else {
        alert("Hata: " + data.message);
      }
    } catch (error: any) {
      if (error?.status === 401) {
        router.push("/login");
        return;
      }
      console.error("Config save error:", error);
      alert("Kaydetme sırasında bir hata oluştu.");
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key: string, value: any) => {
    setConfig(prev => ({ ...prev, [key]: value }));
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
            <h1 className="text-3xl font-bold tracking-tight">Ayarlar</h1>
            <p className="text-muted-foreground">Bot yapılandırması ve parametreler</p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={saving || loading}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Kaydediliyor...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Kaydet
            </>
          )}
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* General Settings */}
          <div className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Settings className="w-5 h-5 text-blue-500" />
                Genel Ayarlar
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-muted-foreground">
                    Döngü Süresi (Saniye)
                  </label>
                  <input
                    type="number"
                    value={config.cycle_duration}
                    onChange={(e) => handleChange("cycle_duration", parseInt(e.target.value))}
                    className="w-full bg-secondary/50 border border-border rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Botun her döngüde ne kadar bekleyeceği (varsayılan: 3600)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-muted-foreground">
                    Trend Limiti
                  </label>
                  <input
                    type="number"
                    value={config.trends_limit}
                    onChange={(e) => handleChange("trends_limit", parseInt(e.target.value))}
                    className="w-full bg-secondary/50 border border-border rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    API'den çekilecek maksimum trend sayısı (varsayılan: 20)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-muted-foreground">
                    Zaman Dilimi (UTC Offset)
                  </label>
                  <div className="flex items-center gap-2 bg-secondary/50 border border-border rounded-lg px-4 py-2">
                    <Globe className="w-4 h-4 text-muted-foreground" />
                    <input
                      type="number"
                      value={config.timezone_offset}
                      onChange={(e) => handleChange("timezone_offset", parseInt(e.target.value))}
                      className="w-full bg-transparent focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Moon className="w-5 h-5 text-purple-500" />
                Uyku Modu
              </h2>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-muted-foreground">
                    Başlangıç Saati (0-23)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="23"
                    value={config.sleep_start}
                    onChange={(e) => handleChange("sleep_start", parseInt(e.target.value))}
                    className="w-full bg-secondary/50 border border-border rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2 text-muted-foreground">
                    Bitiş Saati (0-23)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="23"
                    value={config.sleep_end}
                    onChange={(e) => handleChange("sleep_end", parseInt(e.target.value))}
                    className="w-full bg-secondary/50 border border-border rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-4">
                Bu saatler arasında bot tweet atmaz, sadece trendleri izler.
              </p>
            </div>
          </div>

          {/* AI Settings */}
          <div className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-500" />
                Yapay Zeka Ayarları
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-muted-foreground">
                    Model
                  </label>
                  <select
                    value={config.ai_model}
                    onChange={(e) => handleChange("ai_model", e.target.value)}
                    className="w-full bg-secondary/50 border border-border rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 transition-colors appearance-none"
                  >
                    <option value="gemini-2.5-flash">Gemini 2.5 Flash (Hızlı)</option>
                    <option value="gemini-pro">Gemini Pro (Dengeli)</option>
                    <option value="gemini-ultra">Gemini Ultra (Güçlü)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-muted-foreground">
                    Yaratıcılık (Temperature): {config.temperature}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.temperature}
                    onChange={(e) => handleChange("temperature", parseFloat(e.target.value))}
                    className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>Tutarlı (0.0)</span>
                    <span>Dengeli (0.5)</span>
                    <span>Yaratıcı (1.0)</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-muted-foreground">
                    Maksimum Token
                  </label>
                  <input
                    type="number"
                    value={config.max_tokens}
                    onChange={(e) => handleChange("max_tokens", parseInt(e.target.value))}
                    className="w-full bg-secondary/50 border border-border rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Shield className="w-5 h-5 text-green-500" />
                Güvenlik & Sistem
              </h2>

              <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <h3 className="text-yellow-500 font-medium mb-2">Dikkat</h3>
                <p className="text-sm text-yellow-500/80">
                  Bu ayarlar botun davranışını doğrudan etkiler. Değişiklik yapmadan önce ne yaptığınızdan emin olun.
                  Yanlış yapılandırma botun durmasına veya hatalı çalışmasına neden olabilir.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
