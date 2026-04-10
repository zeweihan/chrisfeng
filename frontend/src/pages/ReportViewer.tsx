import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { DownloadCloud, ArrowLeft, Loader2, Save } from 'lucide-react';

export default function ReportViewer() {
  const { id } = useParams();
  const [htmlContent, setHtmlContent] = useState('');
  const [loading, setLoading] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const res = await axios.get(`/api/reports/${id}`);
        setHtmlContent(res.data.html_content);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [id]);

  const handlePrint = () => {
    if (iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.print();
    }
  };

  const handleSave = async () => {
    if (!iframeRef.current) return;
    try {
      const updatedDoc = iframeRef.current.contentDocument?.documentElement.outerHTML;
      if (!updatedDoc) return;
      await axios.put(`/api/reports/${id}`, {
        html_content: '<!DOCTYPE html>\n' + updatedDoc
      });
      alert('保存修改成功！');
    } catch (e) {
      alert('保存失败');
    }
  };

  return (
    <div className="max-w-7xl mx-auto h-[calc(100vh-6rem)] flex flex-col pt-2">
      <div className="flex items-center justify-between mb-6 shrink-0">
        <Link to="/" className="flex items-center gap-2 text-slate-500 hover:text-slate-800 transition-colors font-medium">
          <ArrowLeft size={18} /> 返回主版
        </Link>
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-400">报告文字支持直接点击修改。修改后点击保存。</span>
          <button 
            onClick={handleSave}
            className="flex items-center gap-2 bg-white text-indigo-600 border border-indigo-200 hover:border-indigo-300 px-5 py-2 rounded-xl font-bold shadow-sm transition-all"
          >
            <Save size={18} /> 保存修改
          </button>
          <button 
            onClick={handlePrint}
            className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white px-5 py-2 rounded-xl font-bold shadow-lg shadow-blue-500/20 transition-all"
          >
            <DownloadCloud size={18} /> 导出为 PDF
          </button>
        </div>
      </div>

      <div className="flex-1 bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200 overflow-hidden relative">
        {loading && (
          <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-md flex items-center justify-center">
            <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
          </div>
        )}
        <iframe 
          ref={iframeRef}
          srcDoc={(htmlContent.includes('<base') ? htmlContent : htmlContent.replace('<head>', '<head><base target="_top">')).replace('</head>', '<style>@media print { @page { margin: 15mm; } * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } body.flex { display: block !important; } body { background: white !important; min-height: auto !important; } main { min-height: auto !important; display: block !important; } .glass-card { background: white !important; backdrop-filter: none !important; -webkit-backdrop-filter: none !important; border: 1px solid #e2e8f0 !important; box-shadow: none !important; page-break-inside: avoid !important; break-inside: avoid-page !important; color: #0f172a !important; } .bg-white\\/90 { background: white !important; backdrop-filter: none !important; -webkit-backdrop-filter: none !important; border: 1px solid #e2e8f0 !important; } section { page-break-inside: auto !important; break-inside: auto !important; padding: 20px 0 !important; border: none !important; } .grid { display: grid !important; } .grid > div { page-break-inside: avoid !important; break-inside: avoid-page !important; } header { page-break-inside: avoid !important; padding: 20px 0 !important; border: none !important; } }</style></head>')}
          className="w-full h-full border-none"
          title="Report Preview"
          sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-modals"
        />
      </div>
    </div>
  );
}
