"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Clock,
  Download,
  PieChart,
  TrendingUp,
  Upload
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart as RechartsPieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

export default function AnalyticsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [successRateData, setSuccessRateData] = useState<any[]>([]);
  const [personaData, setPersonaData] = useState<any[]>([]);
  const [hourlyData, setHourlyData] = useState<any[]>([]);
  const [stats, setStats] = useState({
    totalTweets: 0,
    successRate: 0,
    peakHour: "-",
    mostUsedPersona: "-"
  });

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const [successRes, personaRes, hourlyRes] = await Promise.all([
        fetch("/api/analytics/success_rate"),
        fetch("/api/analytics/personas"),
        fetch("/api/analytics/hourly_activity")
      ]);

      const successJson = await successRes.json();
      const personaJson = await personaRes.json();
      const hourlyJson = await hourlyRes.json();

      setSuccessRateData(Array.isArray(successJson.data) ? successJson.data : []);
      setPersonaData(Array.isArray(personaJson.data) ? personaJson.data : []);
      setHourlyData(Array.isArray(hourlyJson.data) ? hourlyJson.data : []);

      // Calculate summary stats
      const total = Array.isArray(personaJson.data)
        ? personaJson.data.reduce((acc: number, curr: any) => acc + (curr?.value || 0), 0)
        : 0;

      const success = successJson.average || 0;
      const peak = hourlyJson.peak_hour ? `${hourlyJson.peak_hour}:00` : "-";
      const topPersona = Array.isArray(personaJson.data) && personaJson.data.length > 0
        ? personaJson.data[0].name
        : "-";

      setStats({
        totalTweets: total,
        successRate: success,
        peakHour: peak,
        mostUsedPersona: topPersona
      });

    } catch (error) {
      console.error("Analytics fetch error:", error);
    } finally {
      setLoading(false);
    }
  };

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

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
            <h1 className="text-3xl font-bold tracking-tight">İstatistikler</h1>
            <p className="text-muted-foreground">Detaylı bot analizi ve raporlar</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
            <Download className="w-4 h-4" />
            Dışa Aktar
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-muted-foreground text-sm font-medium">Toplam Tweet</span>
            <BarChart3 className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-3xl font-bold">{stats.totalTweets}</div>
        </div>
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-muted-foreground text-sm font-medium">Başarı Oranı</span>
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          </div>
          <div className="text-3xl font-bold">{stats.successRate}%</div>
        </div>
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-muted-foreground text-sm font-medium">En Aktif Saat</span>
            <Clock className="w-4 h-4 text-orange-500" />
          </div>
          <div className="text-3xl font-bold">{stats.peakHour}</div>
        </div>
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-muted-foreground text-sm font-medium">Popüler Persona</span>
            <TrendingUp className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-3xl font-bold truncate">{stats.mostUsedPersona}</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Success Rate Chart */}
        <div className="bg-card border border-border rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-500" />
            Tweet Başarı Oranı (Son 30 Gün)
          </h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={successRateData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" opacity={0.2} />
                <XAxis dataKey="date" stroke="#888" fontSize={12} />
                <YAxis stroke="#888" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Line
                  type="monotone"
                  dataKey="rate"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Persona Distribution */}
        <div className="bg-card border border-border rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-purple-500" />
            Persona Kullanımı
          </h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsPieChart>
                <Pie
                  data={personaData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {Array.isArray(personaData) && personaData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Legend />
              </RechartsPieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Hourly Activity */}
        <div className="bg-card border border-border rounded-xl p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
            <Clock className="w-5 h-5 text-orange-500" />
            Saatlik Aktivite
          </h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" opacity={0.2} />
                <XAxis dataKey="hour" stroke="#888" fontSize={12} />
                <YAxis stroke="#888" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff' }}
                  cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                />
                <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
