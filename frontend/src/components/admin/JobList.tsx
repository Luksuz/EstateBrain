"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ScrapeJob, JobStatus, JobStatusLabels } from "@/types/listing";

interface JobListProps {
  refreshTrigger: number;
}

export function JobList({ refreshTrigger }: JobListProps) {
  const [jobs, setJobs] = useState<ScrapeJob[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchJobs = async () => {
    try {
      const data = await api.getScrapeJobs();
      setJobs(data);
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [refreshTrigger]);

  // Auto-refresh for running jobs
  useEffect(() => {
    const hasRunningJobs = jobs.some(
      (job) => job.status === JobStatus.PENDING || job.status === JobStatus.RUNNING
    );

    if (hasRunningJobs) {
      const interval = setInterval(fetchJobs, 3000);
      return () => clearInterval(interval);
    }
  }, [jobs]);

  const getStatusConfig = (status: JobStatus) => {
    switch (status) {
      case JobStatus.PENDING:
        return {
          classes: "bg-amber-500/15 text-amber-400 border-amber-500/25",
          icon: (
            <svg className="w-3.5 h-3.5 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ),
        };
      case JobStatus.RUNNING:
        return {
          classes: "bg-cyan-500/15 text-cyan-400 border-cyan-500/25",
          icon: (
            <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          ),
        };
      case JobStatus.COMPLETED:
        return {
          classes: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
          icon: (
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ),
        };
      case JobStatus.FAILED:
        return {
          classes: "bg-rose-500/15 text-rose-400 border-rose-500/25",
          icon: (
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ),
        };
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 mx-auto mb-4 bg-slate-800/50 rounded-2xl flex items-center justify-center">
          <svg className="w-8 h-8 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
        <p className="text-slate-400 text-sm">No jobs yet</p>
        <p className="text-slate-500 text-xs mt-1">Create your first scrape job above</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {jobs.map((job) => {
        const statusConfig = getStatusConfig(job.status);
        const progress = job.total_urls > 0 ? (job.processed_urls / job.total_urls) * 100 : 0;
        
        return (
          <div
            key={job.id}
            className="p-4 bg-slate-800/30 border border-slate-700/30 rounded-xl hover:border-slate-600/50 transition-colors"
          >
            <div className="flex items-center justify-between mb-3">
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border ${statusConfig.classes}`}>
                {statusConfig.icon}
                {JobStatusLabels[job.status]}
              </span>
              <span className="text-xs text-slate-500">
                {formatDate(job.created_at)}
              </span>
            </div>

            <div className="mb-3">
              <div className="flex justify-between text-xs text-slate-400 mb-1.5">
                <span>Progress</span>
                <span className="font-mono">
                  {job.processed_urls} / {job.total_urls}
                </span>
              </div>
              <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    job.status === JobStatus.COMPLETED 
                      ? "bg-gradient-to-r from-emerald-500 to-cyan-500"
                      : job.status === JobStatus.FAILED
                      ? "bg-rose-500"
                      : "bg-gradient-to-r from-emerald-500 to-cyan-500"
                  }`}
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[10px] text-slate-600 font-mono">
                ID: {job.id.slice(0, 8)}
              </span>
              {job.status === JobStatus.COMPLETED && (
                <span className="text-[10px] text-emerald-500">
                  ✓ {job.processed_urls} listings processed
                </span>
              )}
            </div>

            {job.error_message && (
              <div className="mt-3 p-2.5 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-300 flex items-start gap-2">
                <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                {job.error_message}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
