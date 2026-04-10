import { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileSpreadsheet, Key, ShieldCheck, Loader2 } from 'lucide-react';

export default function Upload() {
  const [rosterFile, setRosterFile] = useState<File | null>(null);
  const [costFile, setCostFile] = useState<File | null>(null);
  const [salaryFile, setSalaryFile] = useState<File | null>(null);
  const [password, setPassword] = useState('');
  
  const [title, setTitle] = useState('2026年3月人力资源分析报告');
  const [period, setPeriod] = useState('2026年3月');
  const [year] = useState('2026');
  const [month] = useState('3');

  const [provider, setProvider] = useState<'openrouter'|'google'|'kimi'>('openrouter');
  const [model, setModel] = useState('google/gemini-3.1-pro-preview');

  const modelOptions = {
    openrouter: [
      { label: 'Gemini 3.1', value: 'google/gemini-3.1-pro-preview' },
      { label: 'Opus 4.6', value: 'anthropic/claude-opus-4.6' },
      { label: 'GPT 5.4', value: 'openai/gpt-5.4' }
    ],
    google: [
      { label: 'Gemini 3', value: 'gemini-3.1-pro-preview' }
    ],
    kimi: [
      { label: 'Kimi 2.5', value: 'kimi-k2.5' }
    ]
  };

  const handleProviderChange = (newProvider: 'openrouter'|'google'|'kimi') => {
    setProvider(newProvider);
    setModel(modelOptions[newProvider][0].value);
  };

  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const navigate = useNavigate();

  const handleFileUpload = async (file: File, type: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', type);
    if (password) formData.append('password', password);
    
    const res = await axios.post('http://localhost:9169/api/files/upload', formData);
    return res.data.id;
  };

  const handleGenerate = async () => {
    if (!rosterFile) return alert('必传花名册文件');
    
    setLoading(true);
    try {
      setStatusMsg('正在安全脱敏并上传花名册...');
      const roster_file_id = await handleFileUpload(rosterFile, 'roster');
      
      let cost_file_id = null;
      if (costFile) {
        setStatusMsg('正在上传成本数据...');
        cost_file_id = await handleFileUpload(costFile, 'cost');
      }
      
      let salary_file_id = null;
      if (salaryFile) {
        setStatusMsg('正在上传薪酬数据...');
        salary_file_id = await handleFileUpload(salaryFile, 'salary');
      }

      setStatusMsg('AI 正在深度分析各项指标...');

      // Use fetch + SSE stream instead of axios to keep connection alive via heartbeat
      console.log('[SSE] Starting generate request:', { provider, model });
      const response = await fetch('http://localhost:9169/api/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          period,
          year: parseInt(year),
          month: parseInt(month),
          roster_file_id,
          cost_file_id,
          salary_file_id,
          provider,
          model,
        }),
      });

      console.log('[SSE] Response status:', response.status, response.statusText);
      
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        console.error('[SSE] HTTP error:', errData);
        throw new Error(errData.detail || `HTTP ${response.status}`);
      }

      // Read SSE stream
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log('[SSE] Stream ended (done=true). Buffer remaining:', buffer);
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const rawData = line.slice(6);
          try {
            const event = JSON.parse(rawData);
            console.log('[SSE] Event:', event.type, event);
            
            if (event.type === 'heartbeat') {
              const mins = Math.floor(event.elapsed / 60);
              const secs = event.elapsed % 60;
              const timeStr = mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`;
              setStatusMsg(`${event.message}（已用时 ${timeStr}）`);
            } else if (event.type === 'done') {
              console.log('[SSE] ✅ Report generated! ID:', event.id);
              navigate(`/report/${event.id}`);
              return;
            } else if (event.type === 'error') {
              console.error('[SSE] ❌ Server error:', event.message);
              throw new Error(event.message);
            }
          } catch (parseErr: any) {
            // If it's a re-thrown error from our event handling, propagate it
            if (parseErr.message && !parseErr.message.startsWith('Unexpected') && !parseErr.message.startsWith('JSON')) {
              throw parseErr;
            }
            console.warn('[SSE] JSON parse issue (may be partial chunk):', rawData.slice(0, 100));
          }
        }
      }
      
      // If we get here, stream ended without a 'done' or 'error' event
      console.error('[SSE] Stream ended without completion event');
      throw new Error('服务器连接意外中断，请查看后端终端日志');
    } catch (err: any) {
      console.error('[SSE] Final error:', err);
      alert('生成失败: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
      setStatusMsg('');
    }
  };


  return (
    <div className="max-w-4xl mx-auto pt-6">
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold text-slate-800">上传数据并生成洞察</h1>
        <p className="text-slate-500 mt-2">上传包含花名册数据的 Excel 表格，大模型会自动分析人员成分、流动率及核心人才变更。</p>
      </div>

      <div className="bg-white/70 backdrop-blur-xl border border-white/60 rounded-3xl shadow-sm p-8 space-y-8 relative overflow-hidden">
        {loading && (
          <div className="absolute inset-0 bg-white/80 backdrop-blur-md z-50 flex flex-col items-center justify-center">
            <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
            <div className="text-lg font-bold text-slate-800 mb-2">生成中，请耐心等待</div>
            <div className="text-slate-500 text-sm">{statusMsg}</div>
          </div>
        )}

        <div className="bg-emerald-50 border-l-4 border-emerald-500 p-4 rounded-r-xl flex gap-3">
          <ShieldCheck className="text-emerald-500 shrink-0 mt-0.5" />
          <div className="text-emerald-800 text-sm leading-relaxed">
            <strong>自动安全脱敏已启用：</strong><br />
            上传的Excel在发送给大模型前，系统会对“姓名”、“身份证”、“手机号”、“地址”等隐私信息自动替换或去重脱敏（如化名为“员工_001”），保障数据零泄露。
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">报告标题</label>
            <input 
              type="text" 
              className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500/50"
              value={title} onChange={e => setTitle(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">数据周期 (用于展示)</label>
            <input 
              type="text" 
              className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500/50"
              value={period} onChange={e => setPeriod(e.target.value)}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6 pt-4 border-t border-slate-100">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">模型提供商 (Provider)</label>
            <select 
              className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500/50"
              value={provider}
              onChange={(e) => handleProviderChange(e.target.value as 'openrouter'|'google'|'kimi')}
            >
              <option value="openrouter">OpenRouter (中转)</option>
              <option value="google">Google (官方直连)</option>
              <option value="kimi">Kimi (月之暗面)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">底层推理模型 (Model)</label>
            <select 
              className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500/50"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            >
              {modelOptions[provider].map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label} ({opt.value})</option>
              ))}
            </select>
          </div>
        </div>

        <div className="space-y-4">
          <label className="block text-sm font-bold text-slate-700">花名册文件 <span className="text-red-500">*必传</span></label>
          <div className="border-2 border-dashed border-blue-200 rounded-2xl bg-blue-50/50 hover:bg-blue-50 transition-colors p-8 text-center cursor-pointer relative">
            <input type="file" accept=".xlsx,.xls,.csv" className="absolute inset-0 opacity-0 cursor-pointer" onChange={e => setRosterFile(e.target.files?.[0] || null)} />
            <FileSpreadsheet className="w-12 h-12 text-blue-400 mx-auto mb-4" />
            {rosterFile ? (
              <span className="text-blue-700 font-bold">{rosterFile.name} (已选择)</span>
            ) : (
              <div>
                <span className="text-blue-600 font-bold">点击选择花名册 Excel</span>
                <p className="text-slate-400 text-sm mt-1">需包含“在职”与“离职”子表</p>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6 pt-4">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">成本数据分析文件 <span className="text-slate-400 font-normal">(可选)</span></label>
            <div className="border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50 hover:bg-slate-100 transition-colors p-6 text-center cursor-pointer relative">
              <input type="file" accept=".xlsx,.xls,.csv" className="absolute inset-0 opacity-0 cursor-pointer" onChange={e => setCostFile(e.target.files?.[0] || null)} />
              {costFile ? (
                <span className="text-slate-700 font-bold">{costFile.name}</span>
              ) : (
                <span className="text-slate-500 text-sm">点击选择成本 Excel</span>
              )}
            </div>
          </div>
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">薪酬分析文件 <span className="text-slate-400 font-normal">(可选)</span></label>
            <div className="border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50 hover:bg-slate-100 transition-colors p-6 text-center cursor-pointer relative">
              <input type="file" accept=".xlsx,.xls,.csv" className="absolute inset-0 opacity-0 cursor-pointer" onChange={e => setSalaryFile(e.target.files?.[0] || null)} />
              {salaryFile ? (
                <span className="text-slate-700 font-bold">{salaryFile.name}</span>
              ) : (
                <span className="text-slate-500 text-sm">点击选择薪酬 Excel</span>
              )}
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-100">
          <label className="block text-sm font-bold text-slate-700 mb-2">Excel 加密密码 <span className="text-slate-400 font-normal">(如有)</span></label>
          <div className="relative max-w-sm">
            <Key className="absolute left-4 top-3.5 text-slate-400 w-5 h-5" />
            <input 
              type="password" 
              placeholder="文件解密密码" 
              className="w-full bg-white border border-slate-200 rounded-xl pl-12 pr-4 py-3 outline-none focus:ring-2 focus:ring-blue-500/50"
              value={password} onChange={e => setPassword(e.target.value)}
            />
          </div>
        </div>

        <div className="pt-6 flex justify-end">
          <button 
            onClick={handleGenerate}
            className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-bold rounded-xl px-10 py-4 shadow-lg shadow-blue-500/25 transition-all text-lg flex items-center gap-3"
          >
            <UploadCloud size={24} />
            上传并生成报告
          </button>
        </div>
      </div>
    </div>
  );
}
