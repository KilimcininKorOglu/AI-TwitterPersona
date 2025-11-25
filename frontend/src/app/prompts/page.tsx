'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Plus,
  Edit2,
  Trash2,
  X,
  Check,
  AlertCircle,
  Loader2,
  ToggleLeft,
  ToggleRight
} from 'lucide-react';
import { apiFetch } from '../../lib/api';

interface Prompt {
  id: number;
  prompt_type: string;
  prompt_text: string;
  description: string;
  is_active: boolean;
  updated_at: string;
}

export default function PromptsPage() {
  const router = useRouter();
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState<Prompt | null>(null);
  const [formData, setFormData] = useState({
    prompt_type: '',
    prompt_text: '',
    description: '',
    is_active: true
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchPrompts();
  }, []);

  const fetchPrompts = async () => {
    try {
      setLoading(true);
      const res = await apiFetch('/api/prompts');
      const data = await res.json();
      if (data.success) {
        setPrompts(data.prompts);
      } else {
        setError(data.message || 'Promptlar yüklenemedi');
      }
    } catch (err: any) {
      if (err?.status === 401) {
        router.push('/login');
        return;
      }
      setError('Bağlantı hatası');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (prompt?: Prompt) => {
    if (prompt) {
      setEditingPrompt(prompt);
      setFormData({
        prompt_type: prompt.prompt_type,
        prompt_text: prompt.prompt_text,
        description: prompt.description,
        is_active: prompt.is_active
      });
    } else {
      setEditingPrompt(null);
      setFormData({
        prompt_type: '',
        prompt_text: '',
        description: '',
        is_active: true
      });
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingPrompt(null);
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    try {
      const url = editingPrompt
        ? `/api/prompts/${editingPrompt.id}`
        : '/api/prompts';

      const method = editingPrompt ? 'PUT' : 'POST';

      const res = await apiFetch(url, {
        method,
        body: JSON.stringify(formData),
      });

      const data = await res.json();

      if (data.success) {
        fetchPrompts();
        handleCloseModal();
      } else {
        setError(data.message || 'İşlem başarısız');
      }
    } catch (err: any) {
      if (err?.status === 401) {
        router.push('/login');
        return;
      }
      setError('Bir hata oluştu');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Bu promptu silmek istediğinize emin misiniz?')) return;

    try {
      const res = await apiFetch(`/api/prompts/${id}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (data.success) {
        fetchPrompts();
      } else {
        alert(data.message || 'Silme başarısız');
      }
    } catch (err: any) {
      if (err?.status === 401) {
        router.push('/login');
        return;
      }
      alert('Silme işleminde hata oluştu');
    }
  };

  const handleToggle = async (prompt: Prompt) => {
    try {
      // Optimistic update
      const updatedPrompts = prompts.map(p =>
        p.id === prompt.id ? { ...p, is_active: !p.is_active } : p
      );
      setPrompts(updatedPrompts);

      const res = await apiFetch(`/api/prompts/${prompt.prompt_type}/toggle`, {
        method: 'POST',
      });
      const data = await res.json();

      if (!data.success) {
        // Revert on failure
        fetchPrompts();
        alert(data.message || 'Durum değiştirilemedi');
      }
    } catch (err: any) {
      if (err?.status === 401) {
        router.push('/login');
        return;
      }
      fetchPrompts();
      alert('Bağlantı hatası');
    }
  };

  return (
    <div className="min-h-screen bg-black text-white p-8 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/")}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Prompt Yönetimi</h1>
            <p className="text-gray-400">AI persona promptlarını düzenle</p>
          </div>
        </div>
        <button
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2 bg-white text-black px-4 py-2 rounded-full font-medium hover:bg-gray-200 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Yeni Prompt
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-gray-500" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {prompts.map((prompt) => (
            <div
              key={prompt.id}
              className={`bg-gray-900 rounded-xl p-6 border transition-all ${
                prompt.is_active ? 'border-gray-800 hover:border-gray-700' : 'border-red-900/30 opacity-75'
              }`}
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl font-bold">{prompt.prompt_type}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      prompt.is_active ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
                    }`}>
                      {prompt.is_active ? 'Aktif' : 'Pasif'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{prompt.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggle(prompt)}
                    className={`p-2 rounded-lg transition-colors ${
                      prompt.is_active ? 'text-green-400 hover:bg-green-900/20' : 'text-gray-500 hover:bg-gray-800'
                    }`}
                    title={prompt.is_active ? 'Pasife al' : 'Aktifleştir'}
                  >
                    {prompt.is_active ? <ToggleRight className="w-6 h-6" /> : <ToggleLeft className="w-6 h-6" />}
                  </button>
                  <button
                    onClick={() => handleOpenModal(prompt)}
                    className="p-2 text-blue-400 hover:bg-blue-900/20 rounded-lg transition-colors"
                    title="Düzenle"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(prompt.id)}
                    className="p-2 text-red-400 hover:bg-red-900/20 rounded-lg transition-colors"
                    title="Sil"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="bg-black/50 rounded-lg p-3 text-sm text-gray-300 font-mono h-32 overflow-y-auto custom-scrollbar">
                {prompt.prompt_text}
              </div>

              <div className="mt-4 text-xs text-gray-500 flex items-center gap-1">
                <ClockIcon className="w-3 h-3" />
                Güncellendi: {new Date(prompt.updated_at).toLocaleString('tr-TR')}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 rounded-2xl w-full max-w-2xl border border-gray-800 shadow-2xl overflow-hidden">
            <div className="p-6 border-b border-gray-800 flex justify-between items-center">
              <h2 className="text-xl font-bold">
                {editingPrompt ? 'Prompt Düzenle' : 'Yeni Prompt Ekle'}
              </h2>
              <button
                onClick={handleCloseModal}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">
                    Prompt Tipi (ID)
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.prompt_type}
                    onChange={(e) => setFormData({...formData, prompt_type: e.target.value})}
                    disabled={!!editingPrompt} // Disable editing type for existing prompts
                    className="w-full bg-black border border-gray-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                    placeholder="örn: tech, casual"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">
                    Açıklama
                  </label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    className="w-full bg-black border border-gray-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
                    placeholder="Kısa açıklama"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">
                  Prompt Metni
                </label>
                <textarea
                  required
                  value={formData.prompt_text}
                  onChange={(e) => setFormData({...formData, prompt_text: e.target.value})}
                  rows={10}
                  className="w-full bg-black border border-gray-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm"
                  placeholder="Prompt içeriği..."
                />
                <p className="text-xs text-gray-500 mt-1">
                  Değişkenler: {'{persona_name}'}, {'{persona_location}'}, {'{persona_age}'}, ...
                </p>
              </div>

              {error && (
                <div className="bg-red-900/30 text-red-400 p-3 rounded-lg text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  {error}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  İptal
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="bg-white text-black px-6 py-2 rounded-lg font-medium hover:bg-gray-200 transition-colors disabled:opacity-70 flex items-center gap-2"
                >
                  {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                  {editingPrompt ? 'Güncelle' : 'Oluştur'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}
