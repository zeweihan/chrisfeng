import { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { FileText, Plus, Calendar, Trash2 } from 'lucide-react';

interface Report {
  id: number;
  title: string;
  period: string;
  status: string;
  created_at: string;
}

export default function Dashboard() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchReports = async () => {
    try {
      const res = await axios.get('http://localhost:9169/api/reports/list');
      setReports(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const deleteReport = async (id: number) => {
    if (!confirm('确定删除该报告吗？')) return;
    try {
      await axios.delete(`http://localhost:9169/api/reports/${id}`);
      fetchReports();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-800">报告仪表盘</h1>
          <p className="text-slate-500 mt-2">查看历史生成的人力资源分析报告</p>
        </div>
        <Link 
          to="/upload"
          className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white px-5 py-2.5 rounded-xl font-bold shadow-lg shadow-blue-500/20 transition-all transform hover:-translate-y-0.5"
        >
          <Plus size={18} />
          生成新报告
        </Link>
      </div>

      {loading ? (
        <div className="py-20 text-center text-slate-400">加载中...</div>
      ) : reports.length === 0 ? (
        <div className="bg-white/60 backdrop-blur-md rounded-3xl border border-white/60 p-16 text-center shadow-sm">
          <div className="w-20 h-20 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center mx-auto mb-6">
            <FileText size={32} />
          </div>
          <h3 className="text-xl font-bold text-slate-700 mb-2">暂无报告</h3>
          <p className="text-slate-500 mb-6">您还没有生成过任何 HR 数据分析报告。</p>
          <Link 
            to="/upload"
            className="inline-flex items-center gap-2 bg-white text-blue-600 border border-blue-200 hover:border-blue-300 hover:bg-blue-50 px-6 py-3 rounded-xl font-bold transition-all"
          >
            立即生成
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {reports.map((report) => (
            <div key={report.id} className="bg-white/70 backdrop-blur-xl border border-white/60 rounded-3xl p-6 shadow-sm hover:shadow-xl hover:shadow-blue-500/5 transition-all group">
              <div className="w-12 h-12 bg-gradient-to-br from-indigo-100 to-blue-50 text-indigo-600 border border-indigo-100 rounded-xl flex items-center justify-center mb-6">
                <FileText size={24} />
              </div>
              <h3 className="text-lg font-bold text-slate-800 mb-2 group-hover:text-blue-600 transition-colors line-clamp-1">{report.title}</h3>
              <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
                <Calendar size={14} />
                {report.period}
              </div>
              <div className="flex items-center gap-3 pt-6 border-t border-slate-100">
                <Link
                  to={`/report/${report.id}`}
                  className="flex-1 text-center bg-blue-50 hover:bg-blue-100 text-blue-600 py-2.5 rounded-xl font-bold text-sm transition-colors"
                >
                  查看报告
                </Link>
                <button
                  onClick={() => deleteReport(report.id)}
                  className="w-10 h-10 flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-colors"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
