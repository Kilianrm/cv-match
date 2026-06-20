"use client";

import { useEffect, useState } from "react";
import { Briefcase, MapPin, DollarSign, TrendingUp } from "lucide-react";

interface JobMatch {
  id: string;
  title: string;
  company: string;
  location: string;
  work_mode?: string;
  match_score: number;
  description?: string;
}

export default function MatchesPage() {
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchMatches() {
      try {
        // TODO: Replace with actual API endpoint when backend is ready
        // const baseUrl = process.env.NEXT_PUBLIC_API_GATEWAY_BASE_URL || "http://localhost:8080";
        // const res = await fetch(`${baseUrl}/api/v1/matches`, {
        //   credentials: "include",
        // });
        
        // For now, show placeholder
        setMatches([]);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
        setLoading(false);
      }
    }

    fetchMatches();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse">Loading matches...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-foreground">Job Matches</h1>
        <p className="text-muted mt-2">
          Find jobs that match your skills and experience
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {matches.length === 0 && (
        <div className="bg-surface border border-primary/10 rounded-lg p-12 text-center">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
              <Briefcase className="w-8 h-8 text-primary" />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">No matches yet</h3>
          <p className="text-muted mb-6">
            Upload your CV to get started. Once processed, we'll show you jobs that match your
            profile.
          </p>
          <a
            href="/profile"
            className="inline-block px-6 py-3 bg-primary text-background rounded-lg font-semibold hover:bg-primary/90 transition-colors"
          >
            Upload CV Now
          </a>
        </div>
      )}

      {matches.length > 0 && (
        <div className="space-y-4">
          {matches.map((match) => (
            <div
              key={match.id}
              className="bg-surface border border-primary/10 rounded-lg p-6 hover:border-primary/30 transition-colors cursor-pointer"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-foreground">{match.title}</h3>
                  <p className="text-primary font-medium mt-1">{match.company}</p>
                  <div className="flex items-center gap-6 mt-3 flex-wrap">
                    <div className="flex items-center gap-2 text-muted">
                      <MapPin size={16} />
                      <span>{match.location}</span>
                    </div>
                    {match.work_mode && (
                      <span className="text-sm bg-primary/10 text-primary px-3 py-1 rounded-full">
                        {match.work_mode}
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-2 justify-end">
                    <TrendingUp className="w-5 h-5 text-green-600" />
                    <span className="text-2xl font-bold text-green-600">
                      {match.match_score}%
                    </span>
                  </div>
                  <p className="text-sm text-muted">Match Score</p>
                </div>
              </div>

              {match.description && (
                <p className="text-muted mt-4 line-clamp-2">{match.description}</p>
              )}

              <div className="flex gap-3 mt-6">
                <button className="px-4 py-2 bg-primary text-background rounded-lg font-medium hover:bg-primary/90 transition-colors">
                  View Job
                </button>
                <button className="px-4 py-2 border border-primary/20 text-foreground rounded-lg font-medium hover:bg-primary/5 transition-colors">
                  Optimize CV
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
