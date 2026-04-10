import { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings, Save, Loader2 } from 'lucide-react';

interface ConfigItem {
  id: number;
  key: string;
  value: string;
}

export default function Admin() {
  const [configs, setConfigs] = useState<ConfigItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchConfigs = async () => {
      try {
        const res = await axios.get('/api/admin/configs');
        setConfigs(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchConfigs();
  }, []);

  const handleChange = (id: number, val: string) => {
    setConfigs(configs.map(c => c.id === id ? { ...c, value: val } : c));
  };

  const handleSave = async (item: ConfigItem) => {
    setSaving(true);
    try {
      await axios.put(`/api/admin/configs`, { configs: [{ key: item.key, value: item.value }] });
      alert('保存成功');
    } catch (err) {
      alert('保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto pt-6 pb-20">
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 bg-slate-800 rounded-xl flex items-center justify-center text-white shadow-lg shadow-slate-500/20">
          <Settings size={24} />
        </div>
        <div>
          <h1 className="text-3xl font-extrabold text-slate-800">系统配置 (Admin)</h1>
          <p className="text-slate-500 mt-1">定制大模型 System Prompt 与业务解析逻辑</p>
        </div>
      </div>

      <div className="space-y-6">
        {loading ? (
          <div className="flex items-center justify-center p-20"><Loader2 className="w-8 h-8 animate-spin text-slate-400" /></div>
        ) : (
          configs.map((conf) => (
            <div key={conf.id} className="bg-white/70 backdrop-blur-xl border border-white/60 p-6 rounded-2xl shadow-sm">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-slate-700 bg-slate-100 px-3 py-1 rounded-lg text-sm">{conf.key}</h3>
                <button 
                  onClick={() => handleSave(conf)}
                  disabled={saving}
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-900 text-white px-4 py-2 rounded-lg text-sm font-bold shadow-md transition-colors disabled:opacity-50"
                >
                  <Save size={16} /> 保存
                </button>
              </div>
              <textarea 
                className="w-full bg-slate-900 text-green-400 font-mono text-sm p-4 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 h-32 leading-relaxed"
                value={conf.value}
                onChange={e => handleChange(conf.id, e.target.value)}
              />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
